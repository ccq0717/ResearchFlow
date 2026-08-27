import pytest
from sqlalchemy import inspect, text

from researchflow.persistence.database import create_engine, create_schema


async def test_incompatible_schema_is_rejected_before_tables_are_changed() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    await create_schema(engine)
    async with engine.begin() as connection:
        await connection.execute(text("UPDATE schema_migrations SET version = 999"))
        await connection.execute(text("DROP TABLE research_events"))

    with pytest.raises(RuntimeError, match="不兼容"):
        await create_schema(engine)

    async with engine.connect() as connection:
        table_names = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_table_names()
        )
    await engine.dispose()
    assert "research_events" not in table_names
