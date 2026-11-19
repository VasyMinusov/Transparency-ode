"""Схемы экспертной системы: факты, признаки, сигналы, вердикт, НПА."""
from pydantic import BaseModel


class FactOut(BaseModel):
    name: str
    value: str


class IndicatorOut(BaseModel):
    rule: str
    scheme: str
    severity: str
    description: str
    law_refs: list[str]
    action: str = ""          # что запросить у контрагента / какую проверку провести
    methodology: str = ""     # методическое основание (Минтруд / OCP / ГУСП)
    articles: list[ArticleMatch] = []


class ArticleMatch(BaseModel):
    """Подобранная системой статья НПА (legal RAG)."""
    id: str
    act: str
    act_title: str
    article: str
    title: str
    excerpt: str
    score: float


class SignalOut(BaseModel):
    entity_id: int
    entity_name: str
    scheme: str
    rule: str
    severity: str
    description: str
    law_refs: list[str]
    facts: dict[str, str]
    methodology: str = ""
    articles: list[ArticleMatch] = []


class VerdictOut(BaseModel):
    entity_id: int
    level: str           # critical | attention | normal
    level_label: str
    summary: str
    recommendation: str
    facts: list[FactOut]
    indicators: list[IndicatorOut]
    signals: list[SignalOut]
    laws: list[str]


class LawOut(BaseModel):
    id: str
    title: str
    annotation: str


class ContractRow(BaseModel):
    contract_number: str
    date: str
    amount: float
    subject: str
    customer: dict      # {id, name}
    supplier: dict      # {id, name}
    source: str
    check_status: str   # высокая_степень | средняя_степень | в_норме
    severity: str       # high | medium | none


class TenderOut(BaseModel):
    id: int
    subject: str
    procedure: str
    date: str
    submission_days: int
    start_price: float
    customer: dict            # {id, name}
    bids_count: int
    winner: dict | None       # {id, name}
    flags: list[str]          # сработавшие процедурные индикаторы
