"""Pydantic-схемы ответов API."""
from pydantic import BaseModel


class EntityOut(BaseModel):
    id: int
    name: str
    entity_type: str
    external_id: str | None
    attributes: dict

    model_config = {"from_attributes": True}


class RelationOut(BaseModel):
    id: int
    source_id: int
    target_id: int
    relation_type: str
    weight: float
    attributes: dict

    model_config = {"from_attributes": True}


class LoadResult(BaseModel):
    entities_created: int
    relations_created: int
    source: str
