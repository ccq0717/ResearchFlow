import hashlib
import math

from researchflow.integrations.embedding.base import EmbeddingTask


class FakeEmbeddingClient:
    """无需网络的确定性测试适配器，不代表生产语义质量。"""

    def __init__(self, model: str = "fake-embedding", dimensions: int = 32) -> None:
        self._model = model
        self._dimensions = dimensions

    @property
    def model(self) -> str:
        return f"fake:{self._model}:{self._dimensions}"

    async def embed(
        self,
        texts: tuple[str, ...],
        *,
        task: EmbeddingTask,
    ) -> tuple[tuple[float, ...], ...]:
        del task
        return tuple(self._embed_one(text) for text in texts)

    def _embed_one(self, text: str) -> tuple[float, ...]:
        values = [0.0] * self._dimensions
        normalized = "".join(character for character in text.casefold() if character.isalnum())
        features = (normalized[index : index + 2] for index in range(max(1, len(normalized) - 1)))
        for feature in features:
            digest = hashlib.sha256(feature.encode()).digest()
            index = int.from_bytes(digest[:4]) % self._dimensions
            values[index] += 1.0 if digest[4] % 2 else -1.0
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return tuple(value / norm for value in values)
