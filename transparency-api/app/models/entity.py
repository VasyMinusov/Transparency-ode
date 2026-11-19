"""Модели данных: сущности и связи между ними.

SQLite на MVP — осознанное решение: SQLAlchemy + Pydantic дают полную абстракцию,
миграция на PostgreSQL в проде — смена URL в конфиге.
"""
from sqlalchemy import JSON, Float, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    entity_type: Mapped[str] = mapped_column(String, index=True)  # org | person
    external_id: Mapped[str | None] = mapped_column(String, index=True)  # ИНН, СНИЛС
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)


class Relation(Base):
    __tablename__ = "relations"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String, index=True)  # заключен_контракт | работает_в и т.п.
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)  # сумма, номер контракта, дата
