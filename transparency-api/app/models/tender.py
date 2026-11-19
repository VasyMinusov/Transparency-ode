"""Тендеры и заявки: слой конкурентных процедур.

Контракты показывают результат, заявки — процесс. Правила сговора
(идентичные цены, единственный участник, пары соучастников) считаются
только по заявкам. Методика: OCP Red Flags, WB GRAS (категория «сговор»).
"""
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.entity import Base


class Tender(Base):
    __tablename__ = "tenders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True)
    subject: Mapped[str] = mapped_column(String)
    procedure: Mapped[str] = mapped_column(String)   # открытый конкурс | аукцион | запрос котировок | единственный поставщик
    date: Mapped[str] = mapped_column(String)
    submission_days: Mapped[int] = mapped_column(default=20)  # срок подачи заявок, дней
    start_price: Mapped[float] = mapped_column(Float, default=0.0)  # начальная (максимальная) цена
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)    # data_source и пр.


class Bid(Base):
    __tablename__ = "bids"

    id: Mapped[int] = mapped_column(primary_key=True)
    tender_id: Mapped[int] = mapped_column(ForeignKey("tenders.id"), index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True)
    price: Mapped[float] = mapped_column(Float)
    is_winner: Mapped[bool] = mapped_column(Boolean, default=False)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
