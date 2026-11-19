"""Экспертная система выявления коррупционных схем (низходящий ИИ).

Модель: знания о схемах → правила → проверка фактов по данным.
Каждый вывод объясним: цепочка «Факты → Признаки → Сигналы → Вердикт».
Это не обучаемая «чёрная коробка»: правило либо сработало, либо нет,
и всегда видно, на каких фактах основано срабатывание и какие НПА нарушены.
"""
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.legal import query_from_signal, search_articles

from app.models.entity import Entity, Relation

# ── Нормативно-правовая база ──
LAWS: list[dict] = [
    {"id": "fz-44", "title": "44-ФЗ «О контрактной системе в сфере закупок»",
     "annotation": "Конкуренция и процедуры закупок: единственный поставщик, дробление закупок, антидемпинг, требования к участникам."},
    {"id": "fz-273", "title": "273-ФЗ «О противодействии коррупции»",
     "annotation": "Основной антикоррупционный закон: конфликт интересов, обязанности организаций, недопустимость коррупционных проявлений, взаимодействие с контрагентами."},
    {"id": "fz-115", "title": "115-ФЗ «О противодействии легализации доходов, полученных преступным путём»",
     "annotation": "Противодействие отмыванию: идентификация бенефициаров, обязательный контроль сомнительных операций, пороги финансового контроля."},
    {"id": "fz-79", "title": "79-ФЗ «О государственной гражданской службе»",
     "annotation": "Служба и конфликт интересов: ограничения и запреты (ст. 10), уведомление о склонении к коррупционному правонарушению (ст. 17)."},
    {"id": "uk-178", "title": "УК РФ, статья 178",
     "annotation": "Ограничение конкуренции: картельные сговоры на торгах, согласованные действия участников закупок."},
    {"id": "uk-159", "title": "УК РФ, статья 159",
     "annotation": "Мошенничество: хищение чужого имущества, в том числе при закупках и освоении бюджетных средств."},
    {"id": "uk-160", "title": "УК РФ, статья 160",
     "annotation": "Присвоение или растрата: растрата вверенного имущества должностным лицом."},
    {"id": "uk-199", "title": "УК РФ, статья 199",
     "annotation": "Служебный подлог: внесение в документы заведомо ложных сведений, фальсификация итогов закупок."},
    {"id": "uk-204", "title": "УК РФ, статья 204",
     "annotation": "Коммерческий подкуп: неправомерная выгода за действия в пользу дающего в коммерческой деятельности."},
    {"id": "uk-285", "title": "УК РФ, статья 285",
     "annotation": "Злоупотребление должностными полномочиями: действия вопреки интересам службы ради выгоды."},
    {"id": "uk-286", "title": "УК РФ, статья 286",
     "annotation": "Превышение должностных полномочий: действия за пределами полномочий с существенным нарушением прав."},
    {"id": "uk-290", "title": "УК РФ, статья 290",
     "annotation": "Получение взятки: неправомерная выгода должностным лицом за действия (бездействие) в пользу давателя."},
    {"id": "uk-291", "title": "УК РФ, статья 291",
     "annotation": "Дача взятки: передача неправомерной выгоды должностному лицу за нужные действия."},
    {"id": "uk-293", "title": "УК РФ, статья 293",
     "annotation": "Халатность: ненадлежащее исполнение обязанностей по небрежности с крупным ущербом."},
    {"id": "uk-174", "title": "УК РФ, статья 174",
     "annotation": "Легализация (отмывание) доходов, полученных преступным путём — квалификация круговых схем."},
    {"id": "uk-210", "title": "УК РФ, статья 210",
     "annotation": "Организация преступного сообщества — квалификация системных, устойчивых коррупционных схем."},
]


@dataclass
class Fact:
    name: str
    value: str


@dataclass
class Signal:
    scheme: str          # название схемы
    rule: str            # идентификатор правила
    severity: str        # high | medium
    description: str     # объяснение срабатывания (человеческим языком)
    law_refs: list[str]  # идентификаторы НПА
    facts: dict = field(default_factory=dict)
    methodology: str = ""  # методическое основание (Минтруд / OCP / ГУСП)
    articles: list = field(default_factory=list)  # подобранные статьи НПА


@dataclass
class Verdict:
    level: str           # critical | attention | normal
    summary: str
    recommendation: str
    facts: list[Fact]
    indicators: list[dict]   # сработавшие признаки (правила)
    signals: list[Signal]
    laws: list[str]          # все задействованные НПА


METHODOLOGY = {
    "Единоличный поставщик": "Минтруд: концентрация закупок у одного поставщика; OCP R020 (high share of supplier)",
    "Аффилированность (общий адрес)": "Минтруд: массовый адрес регистрации у контрагентов",
    "Аномальная цена контракта": "OCP R010/R017: статистический выброс цены (забор Тьюки Q3+1.5·IQR по заказчику)",
    "Дробление закупок": "Минтруд/ГУСП: дробление для обхода конкурентных процедур",
    "Взаимная зависимость «свой поставщик»": "ГУСП: конфликт интересов, взаимная зависимость заказчика и поставщика",
    "Круговая схема (встречные контракты)": "Типология недолжных способов: круговые схемы; УК-174",
    "Ротация поставщиков": "ФАС: ротация как признак согласованных действий участников",
    "Единичный крупный контракт новому контрагенту": "Минтруд: отсутствие опыта у контрагента при крупной закупке",
    "Срочные закупки в конце года": "ГУСП: авральные закупки в конце года/квартала",
    "Признаки фирмы-однодневки": "Минтруд: недавняя регистрация / минимальный уставный капитал (ЕГРЮЛ)",
    "Единственный участник конкурса": "OCP R018: single bid received; Минтруд: незначительное число участников",
    "Идентичные или кратные цены заявок": "OCP R023/R028: identical bid prices; fixed multiple bid prices",
    "Сговор: постоянный победитель в паре соучастников": "OCP R053: co-bidding pairs с постоянным победителем",
    "Отсечение конкурентов на процедуре": "ГУСП: отклонение заявок конкурентов; типология недолжных способов",
    "Нестандартное авансирование": "44-ФЗ ст. 34 (аванс до 30%); ГУСП: завышение аванса как риск",
    "Злоупотребление закупками у единственного поставщика": "44-ФЗ ст. 93; Минтруд: неконкурентные способы закупки",
    "Массовый руководитель у контрагентов": "115-ФЗ: идентификация выгодоприобретателей; Минтруд: массовый адрес/руководитель",
    "Общий бенефициар с контрагентом": "273-ФЗ: конфликт интересов; 115-ФЗ: бенефициарные владельцы",
}

SIGNAL_ACTIONS = {
    "Единоличный поставщик": "Запросить обоснование выбора поставщика, провести рыночный анализ цен.",
    "Аффилированность (общий адрес)": "Запросить учредительные документы, проверить бенефициаров через ЕГРЮЛ.",
    "Аномальная цена контракта": "Провести сопоставление цены с рыночной, запросить калькуляцию у заказчика.",
    "Дробление закупок": "Проверить, не обходились ли конкурентные процедуры; сверить с планом закупок.",
    "Взаимная зависимость «свой поставщик»": "Проверить декларации о конфликте интересов ответственных лиц.",
    "Круговая схема (встречные контракты)": "Сверить предметы встречных контрактов, запросить акты выполненных работ.",
    "Ротация поставщиков": "Сопоставить сроки и предметы контрактов ротирующихся поставщиков.",
    "Единичный крупный контракт новому контрагенту": "Проверить опыт контрагента, запросить финансовую отчётность и рекомендации.",
    "Срочные закупки в конце года": "Запросить обоснование срочности, проверить движение бюджетных ассигнований.",
    "Отсечение конкурентов на процедуре": "Запросить протоколы рассмотрения заявок и мотивировки отклонений.",
    "Нестандартное авансирование": "Проверить целевое использование аванса, запросить банковские документы.",
    "Злоупотребление закупками у единственного поставщика": "Сверить основания ст. 93 44-ФЗ с фактическими обстоятельствами.",
    "Массовый руководитель у контрагентов": "Запросить справки о доходах руководителя, проверить полномочия подписантов.",
    "Общий бенефициар с контрагентом": "Запросить структуру владения, проверить декларации о конфликте интересов.",
}

LEVEL_LABELS = {
    "critical": "Требует немедленной проверки",
    "attention": "Повышенное внимание",
    "normal": "В норме",
}

RECOMMENDATIONS = {
    "critical": "Передать материалы на проверку: запросить учредительные документы "
                "контрагентов, сопоставить цены с рыночными, рассмотреть на коллегии.",
    "attention": "Включить сущность в план выборочных проверок, запросить пояснения "
                 "ответственных лиц по выявленным признакам.",
    "normal": "Рутинный мониторинг: признаков коррупционных схем не выявлено.",
}


def _analyze_rules(entity: Entity, relations: list[Relation],
                   entities: dict[int, Entity],
                   tenders: list | None = None, bids: list | None = None,
                   ) -> tuple[list[Fact], list[Signal]]:
    """Применяет правила к фактам. Каждое правило — отдельная коррупционная схема.

    Контрактные правила (R1-R10) работают по связям; процедурные (C1-C3) —
    по тендерам и заявкам (методика OCP/WB GRAS, категория «сговор»).
    """
    outgoing = [r for r in relations if r.source_id == entity.id]   # сущность — заказчик
    incoming = [r for r in relations if r.target_id == entity.id]   # сущность — поставщик
    signals: list[Signal] = []
    facts: list[Fact] = []

    def amount(r: Relation) -> float:
        return float(r.attributes.get("amount", 0))

    # ── ФАКТЫ (этап 1: что установлено по данным) ──
    total_out = sum(amount(r) for r in outgoing)
    facts.append(Fact("Контрактов в роли заказчика", str(len(outgoing))))
    facts.append(Fact("Сумма закупок", f"{total_out:,.0f} ₽".replace(",", " ")))
    facts.append(Fact("Контрактов в роли поставщика", str(len(incoming))))

    # ── Правило 1: Единоличный поставщик (заказчик) ──
    if len(outgoing) >= 3:
        by_supplier: dict[int, float] = {}
        for r in outgoing:
            by_supplier[r.target_id] = by_supplier.get(r.target_id, 0) + amount(r)
        top_id, top_sum = max(by_supplier.items(), key=lambda kv: kv[1])
        share = top_sum / total_out if total_out else 0
        facts.append(Fact("Доля крупнейшего поставщика", f"{share:.0%}"))
        facts.append(Fact("Крупнейший поставщик", entities[top_id].name))
        if share > 0.6:
            signals.append(Signal(
                scheme="Единоличный поставщик",
                rule="R1",
                severity="medium",
                description=f"Заказчик разместил {share:.0%} суммы контрактов у одного "
                            f"поставщика ({entities[top_id].name}). Конкуренция фактически отсутствует.",
                law_refs=["fz-44", "uk-178"],
                facts={"поставщик": entities[top_id].name, "доля": f"{share:.0%}",
                       "контрактов": str(sum(1 for r in outgoing if r.target_id == top_id))},
            ))

        # ── Правило 3: Аномальная цена (статистический забор Тьюки, методика OCP) ──
        others = [amount(r) for r in outgoing if r.target_id != top_id]
        top_avg = top_sum / max(1, sum(1 for r in outgoing if r.target_id == top_id))
        if others:
            others_avg = sum(others) / len(others)
            from app.services.statistics import is_outlier
            all_amounts = [amount(r) for r in outgoing]
            if others_avg > 0 and is_outlier(all_amounts, top_avg):
                fence_note = "статистический выброс по распределению заказчика (забор Тьюки)"
                signals.append(Signal(
                    scheme="Аномальная цена контракта",
                    rule="R3",
                    severity="medium",
                    description=f"Средняя сумма контракта с {entities[top_id].name} "
                                f"({top_avg:,.0f} ₽) — {fence_note}; средняя по остальным "
                                f"поставщикам {others_avg:,.0f} ₽.".replace(",", " "),
                    law_refs=["uk-159", "uk-285"],
                    facts={"средняя_с_топ": f"{top_avg:,.0f} ₽".replace(",", " "),
                           "средняя_по_остальным": f"{others_avg:,.0f} ₽".replace(",", " ")},
                ))

        # ── Правило 4: Дробление закупок ──
        top_contracts = [amount(r) for r in outgoing if r.target_id == top_id]
        if len(top_contracts) >= 5:
            max_all = max(amount(r) for r in outgoing)
            top_contracts.sort()
            median_top = top_contracts[len(top_contracts) // 2]
            if max_all > 0 and median_top <= 0.3 * max_all:
                signals.append(Signal(
                    scheme="Дробление закупок",
                    rule="R4",
                    severity="medium",
                    description=f"С одним контрагентом заключено {len(top_contracts)} контрактов "
                                f"на малые суммы (медиана {median_top:,.0f} ₽ при максимуме "
                                f"{max_all:,.0f} ₽) — признак ухода от конкурентных процедур.".replace(",", " "),
                    law_refs=["fz-44", "uk-285"],
                    facts={"контрактов": str(len(top_contracts)),
                           "медиана": f"{median_top:,.0f} ₽".replace(",", " ")},
                ))

    # ── Правило 2: Аффилированность по адресу (заказчик) ──
    supplier_ids = {r.target_id for r in outgoing} | {r.source_id for r in incoming}
    address_map: dict[str, list[str]] = {}
    for sid in supplier_ids:
        addr = (entities[sid].attributes or {}).get("address")
        if addr:
            address_map.setdefault(addr, []).append(entities[sid].name)
    for addr, names in address_map.items():
        if len(names) >= 2:
            signals.append(Signal(
                scheme="Аффилированность (общий адрес)",
                rule="R2",
                severity="high",
                description=f"Контрагенты «{'», «'.join(names)}» зарегистрированы по одному "
                            f"адресу ({addr}) — вероятна скрытая аффилированность.",
                law_refs=["fz-273", "uk-210"],
                facts={"адрес": addr, "контрагенты": ", ".join(names)},
            ))

    # ── Правило 5: Взаимная зависимость «свой поставщик» (поставщик) ──
    if incoming:
        supplier_total = sum(amount(r) for r in incoming)
        by_customer: dict[int, float] = {}
        for r in incoming:
            by_customer[r.source_id] = by_customer.get(r.source_id, 0) + amount(r)
        all_relations = relations
        for cust_id, cust_sum in by_customer.items():
            cust_total = sum(amount(r) for r in all_relations if r.source_id == cust_id)
            if cust_total > 0 and cust_sum / cust_total > 0.5 and cust_sum / supplier_total > 0.5:
                signals.append(Signal(
                    scheme="Взаимная зависимость «свой поставщик»",
                    rule="R5",
                    severity="high",
                    description=f"Поставщик получает {cust_sum / cust_total:.0%} закупок заказчика "
                                f"({entities[cust_id].name}), а этот заказчик даёт {cust_sum / supplier_total:.0%} "
                                f"выручки поставщика — признак устойчивой зависимости.",
                    law_refs=["fz-273", "uk-291"],
                    facts={"заказчик": entities[cust_id].name,
                           "доля_у_заказчика": f"{cust_sum / cust_total:.0%}",
                           "доля_в_выручке": f"{cust_sum / supplier_total:.0%}"},
                ))

    # ── Правило 6: Круговая схема (встречные контракты) ──
    back = {r.source_id for r in incoming}   # кто покупает у сущности
    forth = {r.target_id for r in outgoing}  # у кого покупает сущность
    for cid in forth & back:
        signals.append(Signal(
            scheme="Круговая схема (встречные контракты)",
            rule="R6",
            severity="high",
            description=f"С «{entities[cid].name}» действуют встречные контракты: сущность "
                        f"и закупается у неё, и поставляет ей. Возможна легализация доходов "
                        f"через круговую схему.",
            law_refs=["uk-159", "uk-174"],
            facts={"контрагент": entities[cid].name},
        ))

    # ── Правило 7: Ротация поставщиков ──
    if len(outgoing) >= 6:
        per_sup: dict[int, list[float]] = {}
        for r in outgoing:
            per_sup.setdefault(r.target_id, []).append(amount(r))
        if len(per_sup) >= 3 and all(1 <= len(v) <= 3 for v in per_sup.values()):
            avgs = [sum(v) / len(v) for v in per_sup.values()]
            mean_a = sum(avgs) / len(avgs)
            if mean_a > 0 and (max(avgs) - min(avgs)) / mean_a < 0.7:
                names = [entities[i].name for i in sorted(per_sup, key=lambda i: -len(per_sup[i]))[:4]]
                signals.append(Signal(
                    scheme="Ротация поставщиков",
                    rule="R7",
                    severity="medium",
                    description=f"У заказчика {len(per_sup)} поставщиков с 1-3 контрактами и "
                                f"близкими средними суммами — характерный след ротации "
                                f"(перебивка заказов между «своими» фирмами).",
                    law_refs=["fz-273", "uk-178"],
                    facts={"поставщиков": str(len(per_sup)), "примеры": ", ".join(names)},
                ))

    # ── Правило 8: Единичный крупный контракт новому контрагенту ──
    if len(outgoing) >= 4 and total_out > 0:
        avg_all = total_out / len(outgoing)
        seen: set[int] = set()
        for r in outgoing:
            if r.target_id in seen:
                continue
            seen.add(r.target_id)
            contracts_s = [amount(x) for x in outgoing if x.target_id == r.target_id]
            if len(contracts_s) == 1 and contracts_s[0] > 3 * avg_all:
                signals.append(Signal(
                    scheme="Единичный крупный контракт новому контрагенту",
                    rule="R8",
                    severity="medium",
                    description=f"Контрагент «{entities[r.target_id].name}» получил единственный "
                                f"контракт на {contracts_s[0]:,.0f} ₽ — более чем втрое выше средней "
                                f"суммы заказчика. Проверить опыт и бенефициаров.".replace(",", " "),
                    law_refs=["fz-44", "uk-285"],
                    facts={"контрагент": entities[r.target_id].name,
                           "сумма": f"{contracts_s[0]:,.0f} ₽".replace(",", " ")},
                ))

    # ── Правило 9: Срочные закупки в конце года ──
    if len(outgoing) >= 6:
        q4 = sum(1 for r in outgoing
                 if str((r.attributes or {}).get("date", ""))[5:7] in ("10", "11", "12"))
        if q4 >= 4 and q4 / len(outgoing) >= 0.5:
            signals.append(Signal(
                scheme="Срочные закупки в конце года",
                rule="R9",
                severity="medium",
                description=f"{q4} из {len(outgoing)} контрактов ({q4 / len(outgoing):.0%}) "
                            f"заключены в IV квартале — типичный след «освоения бюджета» в конце года.",
                law_refs=["uk-285", "uk-293"],
                facts={"контрактов_в_q4": str(q4), "всего": str(len(outgoing))},
            ))

    # ── Правило 10: Признаки фирмы-однодневки (ЕГРЮЛ) ──
    if incoming:
        attrs = entity.attributes or {}
        reg = str(attrs.get("registration_date") or "")
        capital = attrs.get("capital")
        first_contract = min(str((r.attributes or {}).get("date", "9999")) for r in incoming)
        young = False
        if reg and len(reg) >= 7 and len(first_contract) >= 7 and reg[:7] < first_contract[:7]:
            months = (int(first_contract[:4]) * 12 + int(first_contract[5:7])) - \
                     (int(reg[:4]) * 12 + int(reg[5:7]))
            young = 0 <= months <= 6
        cheap = isinstance(capital, (int, float)) and capital <= 10_000
        if young or cheap:
            reasons = []
            if young:
                reasons.append(f"зарегистрирована {reg} — менее чем за полгода до первого контракта ({first_contract})")
            if cheap:
                reasons.append(f"уставный капитал {capital:,.0f} ₽ — минимальный".replace(",", " "))
            signals.append(Signal(
                scheme="Признаки фирмы-однодневки",
                rule="R10",
                severity="medium",
                description=f"По данным ЕГРЮЛ-признаков: {'; '.join(reasons)}. "
                            f"Проверить бенефициаров и реальный офис.",
                law_refs=["fz-115", "uk-159"],
                facts={"регистрация": reg, "уставный_капитал": str(capital)},
            ))

    # ══ Процедурные правила сговора (тендеры и заявки, методика OCP/WB GRAS) ══
    my_tenders = [t for t in (tenders or []) if t.customer_id == entity.id]
    if my_tenders and bids:
        bids_by_tender: dict[int, list] = {}
        for b in bids:
            bids_by_tender.setdefault(b.tender_id, []).append(b)

        # ── C1: Единственный участник конкурса ──
        competitive = {"открытый конкурс", "аукцион", "запрос котировок"}
        for t in my_tenders:
            tb = bids_by_tender.get(t.id, [])
            if t.procedure in competitive and len(tb) == 1:
                signals.append(Signal(
                    scheme="Единственный участник конкурса",
                    rule="C1",
                    severity="medium",
                    description=f"Процедура «{t.subject}» ({t.procedure}, {t.date}) состоялась "
                                f"с единственной заявкой — «{entities[tb[0].supplier_id].name}». "
                                f"Конкуренция не состоялась.",
                    law_refs=["fz-44", "uk-178"],
                    facts={"предмет": t.subject, "дата": t.date,
                           "участник": entities[tb[0].supplier_id].name},
                ))

        # ── C2: Идентичные или кратные цены заявок ──
        for t in my_tenders:
            tb = sorted(bids_by_tender.get(t.id, []), key=lambda b: b.price)
            if len(tb) >= 2:
                identical = any(abs(tb[i].price - tb[i + 1].price) / max(tb[i].price, 1) < 0.005
                                for i in range(len(tb) - 1))
                round_mult = all(b.price % 1000 == 0 for b in tb) and len(tb) >= 3
                if identical or round_mult:
                    signals.append(Signal(
                        scheme="Идентичные или кратные цены заявок",
                        rule="C2",
                        severity="medium",
                        description=f"В процедуре «{t.subject}» ({t.date}) цены заявок "
                                    f"{'совпадают с точностью до 0.5%' if identical else 'круглые и кратные 1000'}"
                                    f" — типичный след согласования участников.",
                        law_refs=["uk-178", "uk-204"],
                        facts={"предмет": t.subject,
                               "цены": ", ".join(f"{b.price:,.0f}".replace(",", " ") for b in tb)},
                    ))

        # ── C3: Пара соучастников с постоянным победителем ──
        pair_stats: dict[tuple[int, int], dict] = {}
        for t in my_tenders:
            tb = bids_by_tender.get(t.id, [])
            if len(tb) < 2:
                continue
            winner = next((b.supplier_id for b in tb if b.is_winner), None)
            for b in tb:
                if b.supplier_id == winner:
                    continue
                key = tuple(sorted((b.supplier_id, winner)))
                st = pair_stats.setdefault(key, {"together": 0, "wins": {winner: 0}})
                st["together"] += 1
                st["wins"][winner] = st["wins"].get(winner, 0) + 1
        for (a, b_id), st in pair_stats.items():
            if st["together"] >= 3:
                leader = max(st["wins"], key=st["wins"].get)
                if st["wins"].get(leader, 0) == st["together"]:
                    second = b_id if leader == a else a
                    signals.append(Signal(
                        scheme="Сговор: постоянный победитель в паре соучастников",
                        rule="C3",
                        severity="high",
                        description=f"«{entities[leader].name}» и «{entities[second].name}» "
                                    f"подают заявки вместе {st['together']} раз, и каждый раз побеждает "
                                    f"«{entities[leader].name}». Второй участник систематически играет "
                                    f"роль «технического».",
                        law_refs=["uk-178", "fz-44"],
                        facts={"победитель": entities[leader].name,
                               "вместе": str(st["together"])},
                    ))

# ── Правило 11: Нестандартное авансирование (прецедент: откат через аванс) ──
    advances = [float((r.attributes or {}).get("advance_share", 0.3)) for r in outgoing]
    high_adv = [float(r.attributes.get("amount", 0)) for r in outgoing
                if float((r.attributes or {}).get("advance_share", 0.3)) > 0.5]
    if advances and len(high_adv) >= 2:
        signals.append(Signal(
            scheme="Нестандартное авансирование",
            rule="R11",
            severity="medium",
            description=f"По {len(high_adv)} контрактам аванс превышает 50% (норма 44-ФЗ — до 30%): "
                        f"суммы с авансом {sum(high_adv):,.0f} ₽. Классический след отката через аванс.".replace(",", " "),
            law_refs=["fz-44", "uk-285"],
            facts={"контрактов_с_авансом": str(len(high_adv)),
                   "сумма": f"{sum(high_adv):,.0f} ₽".replace(",", " ")},
        ))

    # ── Правило 12: Злоупотребление закупками у единственного поставщика ──
    if tenders:
        sole = [t for t in tenders if t.customer_id == entity.id
                and t.procedure == "закупка у единственного поставщика"]
        all_t = [t for t in tenders if t.customer_id == entity.id]
        if len(sole) >= 4 and all_t and len(sole) / len(all_t) > 0.4:
            signals.append(Signal(
                scheme="Злоупотребление закупками у единственного поставщика",
                rule="R12",
                severity="medium",
                description=f"{len(sole)} из {len(all_t)} процедур ({len(sole) / len(all_t):.0%}) — закупки "
                            f"у единственного поставщика. Перечень ст. 93 44-ФЗ исчерпывающий; систематическое "
                            f"использование — типичный способ обхода конкуренции.",
                law_refs=["fz-44", "uk-285"],
                facts={"единственный_поставщик": str(len(sole)), "всего": str(len(all_t))},
            ))

    # ── Правило 13: Массовый руководитель у контрагентов ──
    if relations:
        dir_map: dict[str, list[str]] = {}
        for e in entities.values():
            d = (e.attributes or {}).get("director_id")
            if d:
                dir_map.setdefault(d, []).append(e.name)
        involved_ids = {r.target_id for r in outgoing} | {r.source_id for r in incoming} | {entity.id}
        for d, names in dir_map.items():
            hit = [n for i, n in ((i, entities[i].name) for i in involved_ids if i in entities)
                   if (entities[i].attributes or {}).get("director_id") == d]
            if len(hit) >= 3:
                signals.append(Signal(
                    scheme="Массовый руководитель у контрагентов",
                    rule="R13",
                    severity="high",
                    description=f"Один и тот же руководитель ({d}) числится в {len(hit)} организациях "
                                f"контурa сделок: {', '.join(hit)}. Вероятна единая группа под разными вывесками.",
                    law_refs=["fz-115", "uk-210"],
                    facts={"руководитель": d, "организации": ", ".join(hit)},
                ))

    # ── Правило 14: Общий бенефициар с контрагентом ──
    my_founders = (entity.attributes or {}).get("founder_id")
    if my_founders:
        for sid in {r.target_id for r in outgoing} | {r.source_id for r in incoming}:
            se = entities.get(sid)
            if se and (se.attributes or {}).get("founder_id") == my_founders:
                signals.append(Signal(
                    scheme="Общий бенефициар с контрагентом",
                    rule="R14",
                    severity="high",
                    description=f"У сущности и контрагента «{se.name}» совпадает бенефициар "
                                f"({my_founders}) — сделка фактически совершается между связанными лицами. "
                                f"Признак конфликта интересов.",
                    law_refs=["fz-273", "uk-285"],
                    facts={"бенефициар": my_founders, "контрагент": se.name},
                ))

    # ── C4: Отсечение конкурентов (все заявки отклонены, кроме победителя) ──
    if my_tenders and bids:
        for t in my_tenders:
            tb = bids_by_tender.get(t.id, [])
            if len(tb) >= 3:
                admitted = [b for b in tb if (b.attributes or {}).get("admitted", True)]
                if len(admitted) == 1 and admitted[0].is_winner:
                    signals.append(Signal(
                        scheme="Отсечение конкурентов на процедуре",
                        rule="C4",
                        severity="medium",
                        description=f"В процедуре «{t.subject}» ({t.date}) подано {len(tb)} заявок, "
                                    f"но допущена единственная — победитель «{entities[admitted[0].supplier_id].name}». "
                                    f"Остальные отклонены: конкуренция устранена на этапе допуска.",
                        law_refs=["fz-44", "uk-178"],
                        facts={"предмет": t.subject, "заявок": str(len(tb))},
                    ))

    # Обогащение всех сигналов: методическое основание + подбор статей НПА (legal RAG)
    for s in signals:
        if not s.methodology:
            s.methodology = METHODOLOGY.get(s.scheme, "Экспертное правило системы")
        s.articles = search_articles(query_from_signal(s.scheme, s.description, s.facts), top_k=3)
    return facts, signals


async def _load_tender_layer(session: AsyncSession):
    from app.models.tender import Bid, Tender
    tenders = (await session.execute(select(Tender))).scalars().all()
    bids = (await session.execute(select(Bid))).scalars().all()
    return tenders, bids


_verdict_cache: dict[tuple[int, int], Verdict] = {}


async def analyze_entity(session: AsyncSession, entity: Entity) -> Verdict:
    from app.services.datacache import version
    key = (entity.id, version())
    if key in _verdict_cache:
        return _verdict_cache[key]
    relations = (await session.execute(select(Relation))).scalars().all()
    entities = {e.id: e for e in (await session.execute(select(Entity))).scalars().all()}
    tenders, bids = await _load_tender_layer(session)

    facts, signals = _analyze_rules(entity, relations, entities, tenders, bids)
    indicators = [
        {"rule": s.rule, "scheme": s.scheme, "severity": s.severity,
         "description": s.description, "law_refs": s.law_refs,
         "action": SIGNAL_ACTIONS.get(s.scheme, "Запросить письменные пояснения."),
         "methodology": s.methodology, "articles": s.articles}
        for s in signals
    ]
    laws = sorted({ref for s in signals for ref in s.law_refs})
    for s in signals:  # гарантия: у каждого сигнала есть статьи (на случай пустого корпуса)
        if not s.articles:
            from app.services.legal import query_from_signal, search_articles
            s.articles = search_articles(query_from_signal(s.scheme, s.description, s.facts), top_k=3)
    level = ("critical" if any(s.severity == "high" for s in signals)
             else "attention" if signals else "normal")
    verdict = Verdict(
        level=level,
        summary=(f"Выявлено {len(signals)} признаков коррупционных схем."
                 if signals else "Признаков коррупционных схем не выявлено."),
        recommendation=RECOMMENDATIONS[level],
        facts=facts,
        indicators=indicators,
        signals=signals,
        laws=laws,
    )
    _verdict_cache[key] = verdict
    return verdict


_signals_cache: dict[int, list] = {}


async def all_signals(session: AsyncSession) -> list[dict]:
    """Лента сигналов по всем сущностям — для раздела «Сигналы» (кэш по версии)."""
    from app.services.datacache import version
    if version() in _signals_cache:
        return _signals_cache[version()]
    entities = (await session.execute(select(Entity))).scalars().all()
    relations = (await session.execute(select(Relation))).scalars().all()
    tenders, bids = await _load_tender_layer(session)
    emap = {e.id: e for e in entities}
    feed = []
    for e in entities:
        _, signals = _analyze_rules(e, relations, emap, tenders, bids)
        for s in signals:
            feed.append({
                "entity_id": e.id,
                "entity_name": e.name,
                "scheme": s.scheme,
                "rule": s.rule,
                "severity": s.severity,
                "description": s.description,
                "law_refs": s.law_refs,
                "facts": s.facts,
                "methodology": s.methodology,
                "articles": s.articles,
            })
    order = {"high": 0, "medium": 1}
    feed.sort(key=lambda x: (order.get(x["severity"], 2), x["entity_name"]))
    _signals_cache[version()] = feed
    return feed
