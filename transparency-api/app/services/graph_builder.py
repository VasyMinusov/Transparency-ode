"""Построение графа связей из БД и расчёт признаков сущности.

Граф и центральности кэшируются по версии данных: betweenness_centrality
считается один раз за версию, а не на каждый запрос.
"""
import networkx as nx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Relation


_cache: dict = {"v": -1, "graph": None, "between": None}


async def build_graph(session: AsyncSession) -> nx.DiGraph:
    """Граф контрактных связей (кэш по версии данных)."""
    from app.services.datacache import version
    if _cache["graph"] is not None and _cache["v"] == version():
        return _cache["graph"]
    relations = (await session.execute(select(Relation))).scalars().all()
    graph = nx.DiGraph()
    for rel in relations:
        graph.add_edge(rel.source_id, rel.target_id, weight=rel.weight)
    _cache.update({"v": version(), "graph": graph, "between": None})
    return graph


def betweenness_map(graph: nx.DiGraph) -> dict:
    """Кэшированная мапа центральности по посредничеству (раз за версию данных)."""
    if _cache["between"] is None or _cache["graph"] is not graph:
        _cache["between"] = nx.betweenness_centrality(graph)
    return _cache["between"]


def entity_features(graph: nx.DiGraph, entity_id: int) -> dict:
    """Признаки для предиктивной модели. Синтетика → детерминированный расчёт."""
    if entity_id not in graph:
        return {"degree": 0.0, "betweenness": 0.0,
                "contracts_count": 0.0, "weight_ratio": 1.0}

    degree = float(graph.degree(entity_id))
    betweenness = float(betweenness_map(graph).get(entity_id, 0.0))
    contracts_count = float(graph.in_degree(entity_id) + graph.out_degree(entity_id))

    weights = [d["weight"] for *_, d in graph.edges(entity_id, data=True)]
    weights += [d["weight"] for *_, d in graph.in_edges(entity_id, data=True)]
    mean_w = sum(weights) / len(weights) if weights else 0.0
    weight_ratio = round(max(weights) / mean_w, 4) if mean_w > 0 else 1.0

    return {
        "degree": round(degree, 4),
        "betweenness": round(betweenness, 6),
        "contracts_count": contracts_count,
        "weight_ratio": weight_ratio,
    }
