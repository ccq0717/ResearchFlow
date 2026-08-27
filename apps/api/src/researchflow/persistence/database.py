from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, event, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

CURRENT_SCHEMA_VERSION = 1


class Base(DeclarativeBase):
    pass


class SchemaMigrationRow(Base):
    __tablename__ = "schema_migrations"

    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def create_engine(database_url: str) -> AsyncEngine:
    engine = create_async_engine(database_url)
    if database_url.startswith("sqlite"):
        event.listen(
            engine.sync_engine,
            "connect",
            lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"),
        )
    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        current = await connection.scalar(
            select(SchemaMigrationRow.version).order_by(SchemaMigrationRow.version.desc())
        )
        if current is None:
            await connection.execute(
                SchemaMigrationRow.__table__.insert().values(
                    version=CURRENT_SCHEMA_VERSION,
                    applied_at=datetime.now(UTC),
                )
            )
        elif current != CURRENT_SCHEMA_VERSION:
            raise RuntimeError(
                f"数据库结构版本 {current} 与应用版本 {CURRENT_SCHEMA_VERSION} 不兼容"
            )
