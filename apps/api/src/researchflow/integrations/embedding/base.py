from enum import StrEnum
from typing import Protocol


class EmbeddingTask(StrEnum):
    DOCUMENT = "document"
    QUERY = "query"


class EmbeddingClientError(Exception):
    """可安全展示给用户的 Embedding 服务错误。"""

    def __init__(self, code: str, public_message: str) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message


class EmbeddingClient(Protocol):
    """Embedding 模块的深接口：调用方只提交文本并接收同序向量。"""

    @property
    def model(self) -> str: ...

    async def embed(
        self,
        texts: tuple[str, ...],
        *,
        task: EmbeddingTask,
    ) -> tuple[tuple[float, ...], ...]: ...


class UnconfiguredEmbeddingClient:
    @property
    def model(self) -> str:
        return "unconfigured"

    async def embed(
        self,
        texts: tuple[str, ...],
        *,
        task: EmbeddingTask,
    ) -> tuple[tuple[float, ...], ...]:
        del texts
        del task
        raise EmbeddingClientError(
            "EMBEDDING_NOT_CONFIGURED",
            "尚未配置 Embedding 模型，请完成环境变量设置后重新处理文档",
        )
