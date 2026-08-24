from typing import Protocol
from uuid import UUID


class ResearchWorkflow(Protocol):
    """研究工作流对应用层暴露的最小接口。"""

    async def execute(self, run_id: UUID, goal: str) -> None: ...
