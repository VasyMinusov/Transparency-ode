"""Формирование отчёта по сущности в формате DOCX."""
from io import BytesIO

from docx import Document
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity, Relation
from app.services.expert import LEVEL_LABELS, SIGNAL_ACTIONS, analyze_entity
from app.services.graph_builder import build_graph, entity_features
from app.services.level import risk_level
from app.services.predictor import FEATURES, RiskPredictor
from app.services.riskblend import blend_risk

_FACTOR_RU = {
    "degree": "число связей",
    "betweenness": "роль посредника в сети",
    "contracts_count": "число контрактов",
    "weight_ratio": "концентрация сумм (максимум к среднему)",
}


async def build_report_docx(session: AsyncSession, entity: Entity) -> BytesIO:
    graph = await build_graph(session)
    predictor = RiskPredictor.get()
    proba, factors = predictor.predict(entity_features(graph, entity.id))
    verdict = await analyze_entity(session, entity)  # кэшировано
    score = blend_risk(proba, verdict.signals)

    rels = (await session.execute(
        select(Relation).where(
            (Relation.source_id == entity.id) | (Relation.target_id == entity.id))
    )).scalars().all()
    entities = {e.id: e for e in (await session.execute(select(Entity))).scalars().all()}
    cp_acc: dict[int, dict] = {}
    for r in rels:
        cid = r.target_id if r.source_id == entity.id else r.source_id
        acc = cp_acc.setdefault(cid, {"count": 0, "amount": 0.0})
        acc["count"] += 1
        acc["amount"] += float(r.attributes.get("amount", 0))

    doc = Document()
    doc.add_heading(f"Отчёт по сущности: {entity.name}", 0)
    p = doc.add_paragraph()
    p.add_run(f"ИНН: {entity.external_id or 'отсутствует'} · тип: {entity.entity_type}").bold = True
    addr = (entity.attributes or {}).get("address")
    if addr:
        doc.add_paragraph(f"Адрес: {addr}")
    doc.add_paragraph("Основание для проверки, не обвинение. Решение принимает человек.")

    doc.add_heading("Экспертный вердикт", 1)
    doc.add_paragraph(f"Уровень: {LEVEL_LABELS[verdict.level]}")
    doc.add_paragraph(verdict.summary)
    doc.add_paragraph(f"Рекомендация: {verdict.recommendation}")

    doc.add_heading("Факты", 1)
    for f_ in verdict.facts:
        doc.add_paragraph(f"{f_.name}: {f_.value}", style="List Bullet")

    if verdict.signals:
        doc.add_heading("Сигналы", 1)
        for s in verdict.signals:
            doc.add_heading(
                f"[{'высокая' if s.severity == 'high' else 'средняя'} степень] {s.scheme} "
                f"(правило {s.rule})", 2)
            doc.add_paragraph(s.description)
            doc.add_paragraph(f"Методическое основание: {s.methodology}")
            doc.add_paragraph(f"Что запросить: {SIGNAL_ACTIONS.get(s.scheme, 'Запросить письменные пояснения.')}")
            doc.add_paragraph("Нормы: " + ", ".join(s.law_refs))
            if s.articles:
                doc.add_paragraph("Подобранные статьи:", style="List Bullet")
                for art in s.articles[:3]:
                    doc.add_paragraph(
                        f"{art['act']}, {art['article']} «{art['title']}» — {art['excerpt']}",
                        style="List Bullet 2")

    doc.add_heading("Оценка риска", 1)
    doc.add_paragraph(f"Итоговая оценка: {score:.2f} ({risk_level(score)}). "
                      f"Модельная оценка: {proba:.2f}; вклад экспертных правил учтён.")
    doc.add_heading("Факторы модели (SHAP)", 2)
    for f_ in factors:
        name = _FACTOR_RU.get(f_["name"], f_["name"])
        doc.add_paragraph(f"{name}: {f_['value']} (вклад {f_['contribution']:+.3f})",
                          style="List Bullet")

    if cp_acc:
        doc.add_heading("Связанные сущности", 1)
        table = doc.add_table(rows=1, cols=4)
        table.style = "Light Grid Accent 1"
        hdr = table.rows[0].cells
        hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text = "Сущность", "ИНН", "Контрактов", "Сумма, ₽"
        for cid, acc in sorted(cp_acc.items(), key=lambda kv: -kv[1]["amount"]):
            row = table.add_row().cells
            row[0].text = entities[cid].name
            row[1].text = entities[cid].external_id or "—"
            row[2].text = str(acc["count"])
            row[3].text = f"{acc['amount']:,.0f}".replace(",", " ")

    doc.add_heading("Примечания", 1)
    doc.add_paragraph("Оценка построена на синтетическом наборе данных (procurement_mock, tenders_mock) "
                      "и носит характер сигнала для проверки человеком.")
    doc.add_paragraph("Персональные данные не обрабатываются. Актуальные редакции НПА: publication.pravo.gov.ru.")

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
