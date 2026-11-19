"""Оценка качества правил экспертной системы (precision/recall).

Генерирует детерминированный набор размеченных синтетических кейсов:
позитивные (схема заложена конструктором) и негативные (контрольные).
Считает TP/FP/FN по каждому правилу через тот же движок, что и продакшен.

Запуск: uv run python tools/eval_rules.py
Результат: печать таблицы + запись в data/eval_report.json (для паспорта).
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # корень transparency-api

from app.models.entity import Entity, Relation
from app.models.tender import Bid, Tender
from app.services.expert import _analyze_rules

rng = random.Random(42)


def ent(eid: str, name: str, **attrs) -> Entity:
    return Entity(id=int(eid), name=name, entity_type="org",
                  external_id=eid, attributes=attrs)


def rel(rid: str, src: Entity, tgt: Entity, amount: float, date: str,
        data_source: str = "eval_synthetic") -> Relation:
    return Relation(id=int(rid), source_id=src.id, target_id=tgt.id,
                    relation_type="заключен_контракт", weight=amount / 1e6,
                    attributes={"amount": amount, "date": date, "data_source": data_source})


CASES = []  # (название, правило, factory) — factory строит (entities, relations, tenders, bids, target)


def case(name, rule):
    def deco(fn):
        CASES.append((name, rule, fn))
        return fn
    return deco


# ── Позитивные кейсы ──
@case("концентрация у одного поставщика", "R1")
def _():
    cust, sup, other = ent("1", "Заказчик"), ent("2", "Поставщик"), ent("3", "Другой")
    rels = [rel(str(100 + i), cust, sup, 1_000_000, f"2024-{i + 1:02d}-10") for i in range(6)]
    rels.append(rel("199", cust, other, 300_000, "2024-06-10"))
    return {"1": cust, "2": sup, "3": other}, rels, [], [], cust


@case("дробление закупок", "R4")
def _():
    cust, sup, big = ent("1", "Заказчик"), ent("2", "Поставщик"), ent("3", "Крупный")
    rels = [rel(str(100 + i), cust, sup, 180_000 + i * 10_000, f"2024-{i + 1:02d}-05") for i in range(7)]
    rels.append(rel("199", cust, big, 8_000_000, "2024-01-10"))
    return {"1": cust, "2": sup, "3": big}, rels, [], [], cust


@case("круговая схема", "R6")
def _():
    a, b = ent("1", "Организация А"), ent("2", "Организация Б")
    rels = [rel("101", a, b, 2_000_000, "2024-03-10"), rel("102", b, a, 1_800_000, "2024-04-10")]
    return {"1": a, "2": b}, rels, [], [], a


@case("фирма-однодневка", "R10")
def _():
    cust = ent("1", "Заказчик")
    young = ent("2", "Свежая ООО", registration_date="2026-08-10", capital=10_000)
    rels = [rel("101", cust, young, 5_000_000, "2026-11-01")]
    return {"1": cust, "2": young}, rels, [], [], young


@case("единственный участник", "C1")
def _():
    cust, sup = ent("1", "Заказчик"), ent("2", "Участник")
    t = Tender(id=1, customer_id=cust.id, subject="Поставка", procedure="аукцион",
               date="2025-05-10", submission_days=10, start_price=1_000_000)
    bids = [Bid(id=1, tender_id=1, supplier_id=sup.id, price=950_000, is_winner=True)]
    return {"1": cust, "2": sup}, [], [t], bids, cust


@case("идентичные цены", "C2")
def _():
    cust, s1, s2 = ent("1", "Заказчик"), ent("2", "Участник 1"), ent("3", "Участник 2")
    t = Tender(id=1, customer_id=cust.id, subject="Ремонт", procedure="открытый конкурс",
               date="2025-06-10", submission_days=15, start_price=2_000_000)
    bids = [Bid(id=1, tender_id=1, supplier_id=s1.id, price=1_500_000, is_winner=True),
            Bid(id=2, tender_id=1, supplier_id=s2.id, price=1_502_000, is_winner=False)]
    return {"1": cust, "2": s1, "3": s2}, [], [t], bids, cust


@case("пара соучастников", "C3")
def _():
    cust, w, l = ent("1", "Заказчик"), ent("2", "Победитель"), ent("3", "Технический")
    tenders, bids = [], []
    for i in range(4):
        tenders.append(Tender(id=i + 1, customer_id=cust.id, subject=f"Закупка {i}",
                              procedure="аукцион", date=f"2024-{i + 1:02d}-10",
                              submission_days=15, start_price=1_000_000))
        bids.append(Bid(id=2 * i + 1, tender_id=i + 1, supplier_id=w.id,
                        price=850_000 + i * 1000, is_winner=True))
        bids.append(Bid(id=2 * i + 2, tender_id=i + 1, supplier_id=l.id,
                        price=920_000 + i * 1000, is_winner=False))
    return {"1": cust, "2": w, "3": l}, [], tenders, bids, cust


# ── Негативные контрольные кейсы ──
@case("здоровая конкуренция", None)
def _():
    cust = ent("1", "Заказчик")
    sups = [ent(str(i + 2), f"Поставщик {i}") for i in range(4)]
    rels = [rel(str(100 + i), cust, rng.choice(sups), 300_000 + i * 120_000, f"2024-{i % 12 + 1:02d}-10")
            for i in range(8)]
    tenders, bids = [], []
    for i in range(3):
        tenders.append(Tender(id=i + 1, customer_id=cust.id, subject=f"Закупка {i}",
                              procedure="открытый конкурс", date=f"2025-{i + 1:02d}-10",
                              submission_days=20, start_price=1_000_000))
        parts = rng.sample(sups, 3)
        prices = sorted(rng.sample(range(700_000, 950_000, 13_717), 3))
        for j, p in enumerate(prices):
            bids.append(Bid(id=3 * i + j + 1, tender_id=i + 1, supplier_id=parts[j].id,
                            price=p, is_winner=j == 0))
    emap = {"1": cust, **{str(i + 2): s for i, s in enumerate(sups)}}
    return emap, rels, tenders, bids, cust


def main() -> None:
    stats: dict[str, dict] = {}
    pos_total = neg_total = 0
    for name, expect_rule, factory in CASES:
        emap, rels, tenders, bids, target = factory()
        emap = {int(k): v for k, v in emap.items()}  # ключи — числовые id сущностей
        _, signals = _analyze_rules(target, rels, emap, tenders, bids)
        fired = {s.rule for s in signals}
        positive_case = expect_rule is not None
        if positive_case:
            pos_total += 1
            st = stats.setdefault(expect_rule, {"tp": 0, "fp": 0, "fn": 0})
            if expect_rule in fired:
                st["tp"] += 1
            else:
                st["fn"] += 1
        else:
            neg_total += 1
            for r in fired:
                stats.setdefault(r, {"tp": 0, "fp": 0, "fn": 0})["fp"] += 1
        status = "OK " if (expect_rule in fired if positive_case else not fired) else "ПРОПУСК" if positive_case else "ЛОЖНОЕ"
        print(f"  [{status}] {name}: сработало {sorted(fired) or '—'}")

    print("\nПравило   TP  FP  FN   precision  recall")
    report = {"cases": len(CASES), "positive": pos_total, "negative": neg_total, "rules": {}}
    for rule in sorted(stats):
        st = stats[rule]
        prec = st["tp"] / (st["tp"] + st["fp"]) if st["tp"] + st["fp"] else None
        rec = st["tp"] / (st["tp"] + st["fn"]) if st["tp"] + st["fn"] else None
        report["rules"][rule] = {"tp": st["tp"], "fp": st["fp"], "fn": st["fn"],
                                 "precision": prec, "recall": rec}
        fmt = lambda v: f"{v:.2f}" if v is not None else "  — "
        print(f"  {rule:<6} {st['tp']:>2} {st['fp']:>3} {st['fn']:>2}   {fmt(prec)}     {fmt(rec)}")

    out = Path("data/eval_report.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nСохранено: {out}")


if __name__ == "__main__":
    main()
