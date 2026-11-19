"""Восходящий агент: находит связи, идя от данных вверх (подход Palantir).

Гибридная модель:
- НИЗХОДЯЩАЯ часть — экспертная система (правила известных схем -> факты).
  Полностью детерминирована: правило либо сработало, либо нет.
- ВОСХОДЯЩАЯ часть — этот агент: корреляции в данных, которые НЕ зашиты
  в правила (кластеры аффилированности в сети, цепочки зависимостей,
  пересечения сигналов у соседей по графу). Найденные корреляции
  озвучиваются языковой моделью (LLM) — локальной (Ollama) или GigaChat.

Детерминированность: вход агента — структурированные факты и сигналы
(всегда одинаковые при одинаковых данных). LLM только формулирует текст
и кэшируется; в режиме offline агент полностью детерминирован.
"""
import hashlib
import json

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.entity import Entity, Relation
from app.services.expert import Signal, analyze_entity

_cache: dict[str, dict] = {}


# ── Корреляции «снизу вверх»: что видно в данных, но не описано правилами ──
def _correlate(entity: Entity, relations: list[Relation],
               entities: dict[int, Entity], signals: list[Signal]) -> list[dict]:
    findings: list[dict] = []
    outgoing = [r for r in relations if r.source_id == entity.id]
    incoming = [r for r in relations if r.target_id == entity.id]

    # 1. Кластер общего адреса: контрагенты сущности + их соседи по адресу
    addr_of = {e.id: (e.attributes or {}).get("address") for e in entities.values()}
    cluster: dict[str, set[int]] = {}
    for e in entities.values():
        if addr_of.get(e.id):
            cluster.setdefault(addr_of[e.id], set()).add(e.id)
    involved = [c for c in cluster.values() if len(c) >= 2 and (c & {r.target_id for r in outgoing} or c & {r.source_id for r in incoming})]
    for c in involved:
        names = [entities[i].name for i in sorted(c)]
        findings.append({
            "type": "кластер_адресов",
            "description": f"В окружении сущности обнаружен кластер из {len(c)} организаций "
                           f"с общим адресом: {'; '.join(names)}. Проверить бенефициаров.",
            "related": names,
            "related_ids": sorted(c),
        })

    # 2. Пересечение сигналов у контрагентов
    neighbor_signals = [s for s in signals if s["entity_id"] != entity.id]
    if neighbor_signals:
        by_scheme: dict[str, list[str]] = {}
        for s in neighbor_signals:
            by_scheme.setdefault(s["scheme"], []).append(s["entity_name"])
        for scheme, names in by_scheme.items():
            findings.append({
                "type": "пересечение_сигналов",
                "description": f"Признак «{scheme}» встречается у {len(names)} связанных "
                               f"сущностей: {', '.join(names[:5])}. Возможна системная схема, "
                               f"а не разовое нарушение.",
                "related": names,
            })

    # 3. Концентрация потоков через посредников (2-hop)
    neighbors = {r.target_id for r in outgoing} | {r.source_id for r in incoming}
    for n in neighbors:
        n_out = [r for r in relations if r.source_id == n]
        n_in = [r for r in relations if r.target_id == n]
        if len(n_out) + len(n_in) >= 8:
            findings.append({
                "type": "концентрация_потоков",
                "description": f"Контрагент «{entities[n].name}» участвует в "
                               f"{len(n_out) + len(n_in)} контрактах сети — возможная роль "
                               f"посредника/прокладки. Проверить его выручку и учредителей.",
                "related": [entities[n].name],
                "related_ids": [n],
            })
    return findings


# ── Озвучивание корреляций ──
def _plural(n: int, one: str, few: str, many: str) -> str:
    n10, n100 = n % 10, n % 100
    if n10 == 1 and n100 != 11:
        return one
    if 2 <= n10 <= 4 and not (12 <= n100 <= 14):
        return few
    return many


def _offline_narration(entity_name: str, findings: list[dict]) -> str:
    """Сводка человекочитаемым текстом: сгруппирована по смыслу, без повторов."""
    if not findings:
        return (f"Восходящий анализ сети вокруг «{entity_name}» не выявил корреляций "
                "сверх сработавших правил. Рекомендуется периодический пересмотр при обновлении данных.")

    by_type: dict[str, list[dict]] = {}
    for f_ in findings:
        by_type.setdefault(f_["type"], []).append(f_)

    parts = [f"Анализ сети вокруг «{entity_name}» выявил {len(findings)} "
             f"{_plural(len(findings), 'корреляцию', 'корреляции', 'корреляций')}."]

    clusters = by_type.get("кластер_адресов", []) + by_type.get("сетевой_кластер", [])
    if clusters:
        members = sorted({m for c in clusters for m in c.get("related", [])})
        parts.append(
            f"По общим адресам сгруппированы {len(members)} организаций "
            f"({', '.join(members[:6])}{'…' if len(members) > 6 else ''}) — вероятна скрытая "
            f"аффилированность, бенефициаров этих компаний следует установить.")

    crosses = by_type.get("пересечение_сигналов", [])
    if crosses:
        strong = sorted(crosses, key=lambda f_: int(f_.get("facts", {}).get("число_сущностей", 0)),
                        reverse=True)[:3]
        desc = "; ".join(
            f"признак «{f_.get('facts', {}).get('схема', '—')}» — у {f_.get('facts', {}).get('число_сущностей', '—')} "
            f"связанных сущностей" for f_ in strong)
        parts.append(f"Системность: {desc}. Повторяемость одних признаков у разных участников "
                     f"указывает на устойчивую схему, а не разовое нарушение.")

    hubs = by_type.get("концентрация_потоков", []) + by_type.get("узлы_сети", [])
    if hubs:
        names = [f_.get("related", ["—"])[0] for f_ in hubs[:3]]
        parts.append(f"Наибольшую проходимость контрактов имеют: {', '.join(names)} — "
                     f"проверить их роль посредников и финансовые потоки.")

    parts.append("Все корреляции — гипотезы для проверки человеком, не выводы о нарушениях.")
    return " ".join(parts)


def _prompt(entity_name: str, signals: list[Signal], findings: list[dict]) -> str:
    return (
        "Ты — аналитик подразделения по профилактике коррупционных правонарушений. "
        f"Сущность: {entity_name}. "
        f"Сработавшие правила: {[s.scheme for s in signals]}. "
        f"Корреляции в данных: {json.dumps(findings, ensure_ascii=False)}. "
        "Сформулируй сводку: какие связи в данных заслуживают внимания и какие проверки "
        "предложить. 3-5 предложений, только гипотезы, без обвинений. На русском."
    )


async def _gigachat_narration(prompt: str) -> str:
    from gigachat import GigaChat
    client = GigaChat(credentials=settings.gigachat_credentials,
                      scope=settings.gigachat_scope, verify_ssl_certs=False)
    resp = client.chat(prompt)
    return resp.choices[0].message.content


async def _ollama_narration(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=120) as http:
        resp = await http.post(
            f"{settings.ollama_url}/api/generate",
            json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()


async def narrate(prompt: str, fallback: str) -> str:
    """LLM озвучивает корреляции; при недоступности провайдера — детерминированный шаблон."""
    if settings.llm_provider == "gigachat" and settings.gigachat_credentials:
        try:
            return await _gigachat_narration(prompt)
        except Exception:
            return fallback
    if settings.llm_provider == "ollama":
        try:
            return await _ollama_narration(prompt)
        except Exception:
            return fallback
    return fallback


# ── Публичный API агента ──
async def agent_report(session: AsyncSession, entity: Entity) -> dict:
    relations = (await session.execute(select(Relation))).scalars().all()
    entities = {e.id: e for e in (await session.execute(select(Entity))).scalars().all()}
    verdict = await analyze_entity(session, entity)
    signals_all = []
    for e in entities.values():
        _, sigs = __import__("app.services.expert", fromlist=["_analyze_rules"])._analyze_rules(
            e, relations, entities)
        signals_all.extend([{**s.__dict__, "entity_id": e.id, "entity_name": e.name} for s in sigs])

    findings = _correlate(entity, relations, entities, signals_all)
    digest = hashlib.md5(json.dumps(findings, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    key = f"report:{entity.id}:{digest}"
    if key not in _cache:
        fallback = _offline_narration(entity.name, findings)
        text = await narrate(_prompt(entity.name, verdict.signals, findings), fallback)
        _cache[key] = {"narrative": text, "findings": findings, "provider": settings.llm_provider,
                       "cached": False}
    result = dict(_cache[key])
    result["cached"] = key in _cache
    result["findings"] = findings
    return result


async def agent_overview(session: AsyncSession) -> dict:
    """Сводка по всей сети: сетевые кластеры без привязки к одной сущности."""
    relations = (await session.execute(select(Relation))).scalars().all()
    entities = {e.id: e for e in (await session.execute(select(Entity))).scalars().all()}
    addr_clusters: dict[str, list[str]] = {}
    for e in entities.values():
        addr = (e.attributes or {}).get("address")
        if addr:
            addr_clusters.setdefault(addr, []).append(e.name)
    clusters = [{"address": a, "members": n, "member_ids": [e.id for e in entities.values()
                 if (e.attributes or {}).get("address") == a]} for a, n in addr_clusters.items()
                if len(n) >= 2]
    top = sorted(entities.values(), key=lambda e: len([r for r in relations
                 if r.source_id == e.id or r.target_id == e.id]), reverse=True)[:5]
    findings = [
        {"type": "сетевой_кластер",
         "description": f"Адрес «{c['address']}» объединяет {len(c['members'])} организаций: "
                        f"{', '.join(c['members'])}.", "related": c["members"],
         "related_ids": c["member_ids"]}
        for c in clusters
    ]
    findings.append({
        "type": "узлы_сети",
        "description": "Наиболее связанные узлы сети: " +
                       ", ".join(f"«{e.name}»" for e in top) +
                       " — точки максимального влияния на потоки.",
        "related": [e.name for e in top],
        "related_ids": [e.id for e in top],
    })
    digest = hashlib.md5(json.dumps(findings, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    key = f"overview:{digest}"
    if key not in _cache:
        fallback = ("Восходящий анализ сети. " + " ".join(f["description"] for f in findings) +
                    " Все корреляции требуют проверки человеком.")
        prompt = ("Ты — антикоррупционный аналитик. Сетевые корреляции: "
                  f"{json.dumps(findings, ensure_ascii=False)}. "
                  "Сформулируй сводку по сети: главные узлы риска и приоритетные проверки. "
                  "4-6 предложений, только гипотезы. На русском.")
        text = await narrate(prompt, fallback)
        _cache[key] = {"narrative": text, "provider": settings.llm_provider}
    result = dict(_cache[key])
    result["findings"] = findings
    result["entities_count"] = len(entities)
    result["relations_count"] = len(relations)
    return result
