import asyncio
from io import BytesIO
from pathlib import Path

from httpx import ASGITransport, AsyncClient
from pypdf import PdfWriter

from researchflow.app_factory import create_app
from researchflow.core.config import Settings
from researchflow.integrations.embedding.fake import FakeEmbeddingClient
from researchflow.integrations.llm.fake import FakeLLMClient
from researchflow.integrations.web.fake import FakeSearchProvider, FakeWebPageReader


def _settings(tmp_path: Path, *, max_bytes: int = 10 * 1024 * 1024) -> Settings:
    return Settings(
        _env_file=None,
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'knowledge.db').as_posix()}",
        knowledge_upload_directory=tmp_path / "uploads",
        knowledge_max_document_bytes=max_bytes,
        simulation_step_delay=0,
    )


async def test_text_document_upload_persists_chunks_and_uses_safe_storage_name(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    app = create_app(settings, embedding_client=FakeEmbeddingClient())
    content = (
        "# AI 代码评测\n\n正确性需要可重复执行的测试。\n安全性需要独立的静态与动态检查。\n"
    ).encode()

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            uploaded = await client.post(
                "/api/knowledge-documents",
                files={"file": ("../../evaluation.md", content, "text/markdown")},
            )

            assert uploaded.status_code == 201, uploaded.json()
            document = uploaded.json()
            assert document["original_filename"] == "evaluation.md"
            assert document["status"] == "ready"
            assert document["chunk_count"] == 1
            chunks = (await client.get(f"/api/knowledge-documents/{document['id']}/chunks")).json()[
                "items"
            ]
            assert chunks[0]["locator"] == "第 1–4 行"
            assert "可重复执行的测试" in chunks[0]["content"]
            original = await client.get(f"/api/knowledge-documents/{document['id']}/content")
            assert original.content == content
            assert "evaluation.md" in original.headers["content-disposition"]

    stored_files = tuple((tmp_path / "uploads").iterdir())
    assert len(stored_files) == 1
    assert stored_files[0].name != "evaluation.md"
    assert stored_files[0].suffix == ".md"

    reopened = create_app(settings, embedding_client=FakeEmbeddingClient())
    async with reopened.router.lifespan_context(reopened):
        async with AsyncClient(
            transport=ASGITransport(app=reopened), base_url="http://test"
        ) as client:
            documents = (await client.get("/api/knowledge-documents")).json()["items"]
            assert len(documents) == 1
            assert documents[0]["chunk_count"] == 1


async def test_duplicate_unsupported_and_oversized_documents_are_rejected(
    tmp_path: Path,
) -> None:
    app = create_app(
        _settings(tmp_path, max_bytes=1024),
        embedding_client=FakeEmbeddingClient(),
    )
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            first = await client.post(
                "/api/knowledge-documents",
                files={"file": ("notes.txt", b"use reproducible tests", "text/plain")},
            )
            duplicate = await client.post(
                "/api/knowledge-documents",
                files={"file": ("copy.txt", b"use reproducible tests", "text/plain")},
            )
            unsupported = await client.post(
                "/api/knowledge-documents",
                files={"file": ("notes.docx", b"not a docx", "application/octet-stream")},
            )
            oversized = await client.post(
                "/api/knowledge-documents",
                files={"file": ("large.txt", b"x" * 1025, "text/plain")},
            )

            assert first.status_code == 201
            assert duplicate.status_code == 409
            assert duplicate.json()["code"] == "KNOWLEDGE_DOCUMENT_DUPLICATE"
            assert unsupported.status_code == 400
            assert unsupported.json()["code"] == "DOCUMENT_TYPE_UNSUPPORTED"
            assert oversized.status_code == 413
            assert oversized.json()["code"] == "DOCUMENT_TOO_LARGE"


async def test_unconfigured_embedding_is_a_reprocessable_document_failure(
    tmp_path: Path,
) -> None:
    app = create_app(_settings(tmp_path))
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            uploaded = await client.post(
                "/api/knowledge-documents",
                files={"file": ("notes.txt", b"semantic retrieval notes", "text/plain")},
            )

            assert uploaded.status_code == 201
            assert uploaded.json()["status"] == "failed"
            assert uploaded.json()["error_code"] == "EMBEDDING_NOT_CONFIGURED"


async def test_embedding_configuration_change_requires_document_reprocessing(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    first_app = create_app(
        settings,
        embedding_client=FakeEmbeddingClient(model="first-model", dimensions=32),
    )
    async with first_app.router.lifespan_context(first_app):
        async with AsyncClient(
            transport=ASGITransport(app=first_app), base_url="http://test"
        ) as client:
            uploaded = await client.post(
                "/api/knowledge-documents",
                files={"file": ("notes.txt", b"semantic retrieval notes", "text/plain")},
            )
            document_id = uploaded.json()["id"]
            assert uploaded.json()["status"] == "ready"

    changed_app = create_app(
        settings,
        embedding_client=FakeEmbeddingClient(model="second-model", dimensions=64),
    )
    async with changed_app.router.lifespan_context(changed_app):
        async with AsyncClient(
            transport=ASGITransport(app=changed_app), base_url="http://test"
        ) as client:
            rejected = await client.post(
                "/api/research-runs",
                json={
                    "goal": "使用已上传的资料完成一次语义研究",
                    "document_ids": [document_id],
                },
            )
            assert rejected.status_code == 400
            assert rejected.json()["code"] == "EMBEDDING_REPROCESS_REQUIRED"

            reprocessed = await client.post(f"/api/knowledge-documents/{document_id}/reprocess")
            assert reprocessed.status_code == 200
            assert reprocessed.json()["status"] == "ready"

            created = await client.post(
                "/api/research-runs",
                json={
                    "goal": "使用已上传的资料完成一次语义研究",
                    "document_ids": [document_id],
                },
            )
            assert created.status_code == 201


async def test_text_pdf_is_ready_and_scanned_pdf_can_be_reprocessed_then_deleted(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    app = create_app(settings, embedding_client=FakeEmbeddingClient())
    text_pdf = _text_pdf("AI evaluation requires reproducible tests.")
    blank_pdf_stream = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(blank_pdf_stream)

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            parsed = await client.post(
                "/api/knowledge-documents",
                files={"file": ("paper.pdf", text_pdf, "application/pdf")},
            )
            assert parsed.status_code == 201, parsed.json()
            assert parsed.json()["status"] == "ready"
            parsed_chunks = (
                await client.get(f"/api/knowledge-documents/{parsed.json()['id']}/chunks")
            ).json()["items"]
            assert parsed_chunks[0]["page_number"] == 1
            assert "reproducible tests" in parsed_chunks[0]["content"]

            stored_pdf = next((tmp_path / "uploads").glob("*.pdf"))
            stored_pdf.write_bytes(blank_pdf_stream.getvalue())
            failed_reprocess = await client.post(
                f"/api/knowledge-documents/{parsed.json()['id']}/reprocess"
            )
            assert failed_reprocess.json()["status"] == "failed"
            cleared_chunks = await client.get(
                f"/api/knowledge-documents/{parsed.json()['id']}/chunks"
            )
            assert cleared_chunks.json()["items"] == []

            scanned = await client.post(
                "/api/knowledge-documents",
                files={"file": ("scan.pdf", blank_pdf_stream.getvalue(), "application/pdf")},
            )
            assert scanned.status_code == 201
            assert scanned.json()["status"] == "failed"
            assert scanned.json()["error_code"] == "DOCUMENT_NO_TEXT"

            reprocessed = await client.post(
                f"/api/knowledge-documents/{scanned.json()['id']}/reprocess"
            )
            assert reprocessed.status_code == 200
            assert reprocessed.json()["status"] == "failed"

            deleted = await client.delete(f"/api/knowledge-documents/{scanned.json()['id']}")
            assert deleted.status_code == 204
            missing = await client.get(f"/api/knowledge-documents/{scanned.json()['id']}")
            assert missing.status_code == 404
    assert len(tuple((tmp_path / "uploads").iterdir())) == 1


async def test_selected_local_document_joins_web_research_and_keeps_locator(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path).model_copy(
        update={
            "workflow_mode": "langgraph",
            "llm_model": "fake-model",
            "web_search_result_limit": 2,
        }
    )
    app = create_app(
        settings,
        llm_client=FakeLLMClient(),
        embedding_client=FakeEmbeddingClient(),
        search_provider=FakeSearchProvider(),
        page_reader=FakeWebPageReader(),
    )
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            uploaded = await client.post(
                "/api/knowledge-documents",
                files={
                    "file": (
                        "team-evaluation-notes.md",
                        (
                            "# 团队评测笔记\n\n代码生成评测指标包括可重复测试、安全审查与开发效率。"
                        ).encode(),
                        "text/markdown",
                    )
                },
            )
            document_id = uploaded.json()["id"]
            created = await client.post(
                "/api/research-runs",
                json={
                    "goal": "结合团队本地资料和公开网页设计 AI 代码生成工具评测方案",
                    "document_ids": [document_id],
                },
            )
            run_id = created.json()["id"]
            for _ in range(200):
                detail = await client.get(f"/api/research-runs/{run_id}")
                if detail.json()["status"] in {"completed", "failed"}:
                    break
                await asyncio.sleep(0.01)

            assert detail.json()["status"] == "completed", detail.json()
            materials = (await client.get(f"/api/research-runs/{run_id}/materials")).json()
            local_sources = [
                source for source in materials["sources"] if source["origin"] == "local"
            ]
            assert len(local_sources) == 1
            assert local_sources[0]["knowledge_document_id"] == document_id
            assert local_sources[0]["locator"] == "第 1–3 行"
            assert local_sources[0]["url"] is None
            assert local_sources[0]["title"] in detail.json()["report_markdown"]
            assert local_sources[0]["locator"] in detail.json()["report_markdown"]

            reprocessed = await client.post(f"/api/knowledge-documents/{document_id}/reprocess")
            assert reprocessed.status_code == 200
            assert document_id in {
                str(item)
                for item in await app.state.knowledge_library.list_run_document_ids(run_id)
            }

            deleted = await client.delete(f"/api/knowledge-documents/{document_id}")
            assert deleted.status_code == 204
            assert await app.state.knowledge_library.list_run_document_ids(run_id) == ()


def _text_pdf(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("ascii")
    objects = (
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    )
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, item in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(item)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    return bytes(output)
