from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class DocumentParsingError(Exception):
    def __init__(self, code: str, public_message: str) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message


@dataclass(frozen=True, slots=True)
class ParsedChunk:
    content: str
    locator: str
    page_number: int | None = None
    start_line: int | None = None
    end_line: int | None = None


def parse_document(
    filename: str,
    data: bytes,
    *,
    chunk_size: int,
    max_extracted_characters: int,
    max_pdf_pages: int,
    max_pdf_page_stream_bytes: int,
) -> tuple[ParsedChunk, ...]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return _parse_pdf(
            data,
            chunk_size=chunk_size,
            max_extracted_characters=max_extracted_characters,
            max_pages=max_pdf_pages,
            max_page_stream_bytes=max_pdf_page_stream_bytes,
        )
    if suffix in {".md", ".markdown", ".txt"}:
        return _parse_text(
            data,
            chunk_size=chunk_size,
            max_extracted_characters=max_extracted_characters,
        )
    raise DocumentParsingError("DOCUMENT_TYPE_UNSUPPORTED", "仅支持 PDF、Markdown 和纯文本文件")


def _parse_text(
    data: bytes,
    *,
    chunk_size: int,
    max_extracted_characters: int,
) -> tuple[ParsedChunk, ...]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise DocumentParsingError(
            "DOCUMENT_ENCODING_UNSUPPORTED",
            "Markdown 和纯文本文件必须使用 UTF-8 编码",
        ) from error
    if len(text) > max_extracted_characters:
        raise DocumentParsingError("DOCUMENT_TEXT_TOO_LARGE", "文档可提取文本超过处理上限")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    chunks = _chunk_lines(lines, chunk_size=chunk_size)
    if not chunks:
        raise DocumentParsingError("DOCUMENT_NO_TEXT", "文档中没有可检索的文本")
    return chunks


def _parse_pdf(
    data: bytes,
    *,
    chunk_size: int,
    max_extracted_characters: int,
    max_pages: int,
    max_page_stream_bytes: int,
) -> tuple[ParsedChunk, ...]:
    if not data.startswith(b"%PDF-"):
        raise DocumentParsingError("DOCUMENT_INVALID_PDF", "文件扩展名为 PDF，但内容不是有效 PDF")
    try:
        reader = PdfReader(BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise DocumentParsingError("DOCUMENT_PDF_ENCRYPTED", "暂不支持加密 PDF")
        if len(reader.pages) > max_pages:
            raise DocumentParsingError(
                "DOCUMENT_PDF_TOO_MANY_PAGES",
                f"PDF 页数不能超过 {max_pages} 页",
            )
        chunks: list[ParsedChunk] = []
        extracted_character_count = 0
        for page_number, page in enumerate(reader.pages, start=1):
            contents = page.get_contents()
            if contents is not None and len(contents.get_data()) > max_page_stream_bytes:
                raise DocumentParsingError(
                    "DOCUMENT_PDF_PAGE_TOO_COMPLEX",
                    f"PDF 第 {page_number} 页内容流过大，无法安全解析",
                )
            page_text = page.extract_text() or ""
            extracted_character_count += len(page_text)
            if extracted_character_count > max_extracted_characters:
                raise DocumentParsingError(
                    "DOCUMENT_TEXT_TOO_LARGE",
                    "PDF 可提取文本超过处理上限",
                )
            for content in _chunk_text(page_text, chunk_size=chunk_size):
                chunks.append(
                    ParsedChunk(
                        content=content,
                        locator=f"第 {page_number} 页",
                        page_number=page_number,
                    )
                )
    except DocumentParsingError:
        raise
    except (PdfReadError, OSError, ValueError) as error:
        raise DocumentParsingError("DOCUMENT_INVALID_PDF", "无法解析该 PDF 文件") from error
    if not chunks:
        raise DocumentParsingError(
            "DOCUMENT_NO_TEXT",
            "PDF 中没有可提取文本；当前版本不包含 OCR",
        )
    return tuple(chunks)


def _chunk_lines(lines: list[str], *, chunk_size: int) -> tuple[ParsedChunk, ...]:
    chunks: list[ParsedChunk] = []
    buffer: list[str] = []
    start_line = 1
    for line_number, line in enumerate(lines, start=1):
        if len(line) > chunk_size:
            content = "\n".join(buffer).strip()
            if content:
                chunks.append(
                    ParsedChunk(
                        content=content,
                        locator=f"第 {start_line}–{line_number - 1} 行",
                        start_line=start_line,
                        end_line=line_number - 1,
                    )
                )
            chunks.extend(
                ParsedChunk(
                    content=part,
                    locator=f"第 {line_number} 行",
                    start_line=line_number,
                    end_line=line_number,
                )
                for part in _chunk_text(line, chunk_size=chunk_size)
            )
            buffer = []
            start_line = line_number + 1
            continue
        candidate = "\n".join((*buffer, line)).strip()
        if buffer and len(candidate) > chunk_size:
            content = "\n".join(buffer).strip()
            if content:
                chunks.append(
                    ParsedChunk(
                        content=content,
                        locator=f"第 {start_line}–{line_number - 1} 行",
                        start_line=start_line,
                        end_line=line_number - 1,
                    )
                )
            buffer = [line]
            start_line = line_number
        else:
            buffer.append(line)
    content = "\n".join(buffer).strip()
    if content:
        chunks.append(
            ParsedChunk(
                content=content,
                locator=f"第 {start_line}–{len(lines)} 行",
                start_line=start_line,
                end_line=len(lines),
            )
        )
    return tuple(chunks)


def _chunk_text(text: str, *, chunk_size: int) -> tuple[str, ...]:
    normalized = "\n".join(line.strip() for line in text.splitlines()).strip()
    if not normalized:
        return ()
    paragraphs = [item.strip() for item in normalized.split("\n\n") if item.strip()]
    chunks: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            chunks.extend(
                paragraph[start : start + chunk_size]
                for start in range(0, len(paragraph), chunk_size)
            )
        elif buffer and len(buffer) + len(paragraph) + 2 > chunk_size:
            chunks.append(buffer)
            buffer = paragraph
        else:
            buffer = f"{buffer}\n\n{paragraph}" if buffer else paragraph
    if buffer:
        chunks.append(buffer)
    return tuple(chunks)
