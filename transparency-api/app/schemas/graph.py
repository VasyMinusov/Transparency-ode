"""Схемы графа для визуализации."""
from pydantic import BaseModel


class GraphNode(BaseModel):
    id: int
    name: str
    entity_type: str
    risk_score: float
    risk_level: str  # low | medium | high


class GraphEdge(BaseModel):
    source: int
    target: int
    relation_type: str
    weight: float


class GraphPayload(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
