// Отчётная страница по сущности: вердикт экспертной системы, оценка риска,
// факторы, гипотеза, таблица связей. Граф сознательно не используется:
// при более чем ~10 узлах он нечитаем — отчёт читается всегда.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode, type ReactElement } from "react";
import { primarySource } from "../data/sources";
import {
  FACTOR_LABELS, SOURCE_LABELS, type Report, type RiskLevel,
} from "../data/types";
import AgentBlock from "./AgentBlock";
import Expandable from "./Expandable";
import { AmountBars, MiniGraph, SignalsDonut } from "./Charts";
import VerdictBlock from "./VerdictBlock";

const LEVEL_LABEL: Record<RiskLevel, string> = { low: "Низкий", medium: "Средний", high: "Высокий" };

function formatMoney(v: number): string {
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)} млрд ₽`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)} млн ₽`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(0)} тыс. ₽`;
  return `${v.toFixed(0)} ₽`;
}

function Section({ title, tip, children, defaultOpen = true }: {
  title: string; tip?: string; children: ReactElement; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="card">
      <h3 className="section-head" onClick={() => setOpen((v) => !v)}>
        <span className="section-caret">{open ? "▾" : "▸"}</span> {title}
        {tip && <span className="tip" data-tip={tip}>?</span>}
      </h3>
      {open && children}
    </div>
  );
}

function KpiCard({ label, value, hint }: { label: string; value: string; hint?: ReactNode }) {
  return (
    <div className="card kpi">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {hint && <div className="kpi-hint">{hint}</div>}
    </div>
  );
}

function FactorsBlock({ report }: { report: Report }) {
  const maxAbs = Math.max(...report.factors.map((f) => Math.abs(f.contribution)), 0.001);
  return (
    <div className="card">
      <h3>
        Факторы оценки риска
        <span className="tip" data-tip="Вклад каждого признака в оценку риска. Метод Шепли: чем длиннее полоса, тем сильнее признак повлиял на результат">?</span>
      </h3>
      <p className="muted">Почему модель дала именно такую оценку — вклад каждого признака.</p>
      {report.factors.map((f) => (
        <div className="factor" key={f.name}>
          <div className="factor-head">
            <span>{FACTOR_LABELS[f.name] ?? f.name}</span>
            <span className="mono muted">
              {f.value} · вклад {f.contribution >= 0 ? "+" : ""}{f.contribution.toFixed(3)}
            </span>
          </div>
          <div className="factor-track">
            <div
              className={`factor-bar ${f.contribution >= 0 ? "up" : "down"}`}
              style={{ width: `${(Math.abs(f.contribution) / maxAbs) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function CounterpartiesTable({ report, onSelect }: { report: Report; onSelect: (id: number) => void }) {
  return (
    <div className="card">
      <h3>Связанные сущности</h3>
      <p className="muted">
        Контрагенты, отсортированные по оценке риска. Клик по строке — отчёт по этой сущности.
      </p>
      <table className="table">
        <thead>
          <tr>
            <th>Сущность</th><th>ИНН</th><th>Тип связи</th>
            <th className="num">Контрактов</th><th className="num">Сумма</th><th>Риск</th>
          </tr>
        </thead>
        <tbody>
          {report.counterparties.map((c) => (
            <tr key={c.entity.id} onClick={() => onSelect(c.entity.id)}>
              <td>{c.entity.name}</td>
              <td className="mono">{c.entity.external_id ?? "—"}</td>
              <td>{c.relation_types.join(", ")}</td>
              <td className="num">{c.relation_count}</td>
              <td className="num">{formatMoney(c.total_amount)}</td>
              <td>
                <span className={`badge ${c.risk_level}`}>{LEVEL_LABEL[c.risk_level]}</span>{" "}
                <span className="mono muted">{c.risk_score.toFixed(2)}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ReportView({ id, onSelect }: { id: number; onSelect: (id: number) => void }) {
  const { data: report, isLoading, error } = useQuery({
    queryKey: ["report", id],
    queryFn: () => primarySource().getReport(id),
  });
  // Вердикт запрашивается и в VerdictBlock — тот же ключ, запрос один
  const { data: verdict } = useQuery({
    queryKey: ["verdict", id],
    queryFn: () => primarySource().getVerdict(id),
  });
  const { data: contracts } = useQuery({
    queryKey: ["contracts"],
    queryFn: () => primarySource().getContracts(),
  });
  const { data: decisions } = useQuery({
    queryKey: ["decisions"],
    queryFn: () => primarySource().listDecisions(),
  });
  const entityContracts = (contracts ?? []).filter(
    (c) => c.customer.id === id || c.supplier.id === id
  );
  const latestDecision = decisions?.find((d) => d.entity_id === id);

  // Экспорт отчёта: текстовый файл со всеми разделами
  const exportReport = () => {
    if (!report) return;
    const L: string[] = [];
    L.push(`ОТЧЁТ ПО СУЩНОСТИ: ${report.entity.name}`);
    L.push(`ИНН: ${report.entity.external_id ?? "отсутствует"} · тип: ${report.entity.entity_type}`);
    const addr = report.entity.attributes?.address as string | undefined;
    if (addr) L.push(`Адрес: ${addr}`);
    L.push(`Сформирован: ${new Date(report.generated_at).toLocaleString("ru-RU")}`);
    L.push(`Источники данных: ${report.sources.join(", ")}`);
    L.push("");
    if (verdict) {
      L.push(`ВЕРДИКТ: ${verdict.level_label}. ${verdict.summary}`);
      L.push(`Рекомендация: ${verdict.recommendation}`);
      L.push("");
      L.push("ФАКТЫ:");
      verdict.facts.forEach((f) => L.push(`  · ${f.name}: ${f.value}`));
      if (verdict.signals.length) {
        L.push("");
        L.push("СИГНАЛЫ:");
        verdict.signals.forEach((s) => {
          L.push(`  ! [${s.severity === "high" ? "высокая" : "средняя"}] ${s.scheme}`);
          L.push(`    ${s.description}`);
          L.push(`    Основания: ${s.law_refs.join(", ")}`);
        });
      }
    }
    L.push("");
    L.push(`ОЦЕНКА РИСКА: ${report.risk_score.toFixed(2)} (${report.risk_level})`);
    L.push("ФАКТОРЫ ОЦЕНКИ:");
    report.factors.forEach((f) => L.push(`  · ${FACTOR_LABELS[f.name] ?? f.name}: ${f.value} (вклад ${f.contribution.toFixed(3)})`));
    L.push("");
    L.push("ГИПОТЕЗА:");
    L.push(`  ${report.hypothesis}`);
    L.push("");
    L.push("СВЯЗАННЫЕ СУЩНОСТИ:");
    report.counterparties.forEach((c) =>
      L.push(`  · ${c.entity.name} (${c.entity.external_id ?? "—"}): риск ${c.risk_score.toFixed(2)}, ${c.relation_count} контр., ${c.total_amount.toFixed(0)} ₽`));
    if (entityContracts.length) {
      L.push("");
      L.push("КОНТРАКТЫ СУЩНОСТИ:");
      entityContracts.forEach((c) =>
        L.push(`  · ${c.contract_number} от ${c.date}: ${c.subject}, ${c.amount.toFixed(0)} ₽ [${c.check_status}]`));
    }
    if (latestDecision) {
      L.push("");
      L.push(`РЕШЕНИЕ СОТРУДНИКА: ${latestDecision.decision === "confirmed" ? "подтверждён" : "отклонён"} (${new Date(latestDecision.created_at).toLocaleString("ru-RU")})${latestDecision.comment ? ` — ${latestDecision.comment}` : ""}`);
    }
    L.push("");
    L.push(report.data_note);
    L.push("Сигналы носят характер оснований для проверки и не являются обвинением.");
    const blob = new Blob([L.join("\n")], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `отчёт_${report.entity.name.replaceAll("«", "").replaceAll("»", "")}_${id}.txt`;
    a.click();
    URL.revokeObjectURL(a.href);
  };
  const [comment, setComment] = useState("");
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: primarySource().submitDecision,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["decisions"] }); setComment(""); },
  });

  if (isLoading) return <div className="report"><div className="card skeleton">Формируем отчёт…</div></div>;
  if (error || !report) return <div className="report"><div className="card">Не удалось сформировать отчёт.</div></div>;

  const totalContracts = report.counterparties.reduce((s, c) => s + c.relation_count, 0);
  const totalAmount = report.counterparties.reduce((s, c) => s + c.total_amount, 0);
  const generated = new Date(report.generated_at).toLocaleString("ru-RU");

  return (
    <div className="report">
      <div className="report-toolbar">
        <button className="btn ghost" onClick={exportReport} data-tip="Скачать полный текстовый отчёт: вердикт, факты, сигналы, факторы, связи, контракты">
          Скачать отчёт
        </button>
        <a className="btn ghost" data-tip="Скачать отчёт в формате Word: вердикт, факты, сигналы с подобранными статьями НПА, таблица связей"
           href={`http://127.0.0.1:8000/api/v1/entities/${id}/report.docx`} download>
          Отчёт DOCX
        </a>
      </div>
      <div className="card report-head">
        <div>
          <div className="entity-name">{report.entity.name}</div>
          <div className="muted">
            <span className="mono">{report.entity.external_id ?? "ИНН отсутствует"}</span>
            {" · "}{report.entity.entity_type === "org" ? "Организация" : "Физическое лицо"}
            {(report.entity.attributes?.address as string) &&
              <>{" · "}{report.entity.attributes.address as string}</>}
            {" · отчёт сформирован "}{generated}
          </div>
          {latestDecision && (
            <div className="muted small" style={{ marginTop: 4 }}>
              Решение сотрудника: {latestDecision.decision === "confirmed" ? "сигнал подтверждён" : "сигналы отклонены (сохранены для истории)"}
              {" · "}{new Date(latestDecision.created_at).toLocaleString("ru-RU")}
            </div>
          )}
        </div>
        <div className="report-actions">
          <input
            className="input"
            placeholder="Комментарий к решению"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          <div className="btn-row">
            <button className="btn" onClick={() => mutation.mutate({ entity_id: id, decision: "confirmed", comment })}>
              Подтвердить сигнал
            </button>
            <button className="btn ghost" onClick={() => mutation.mutate({ entity_id: id, decision: "rejected", comment })}>
              Отклонить
            </button>
          </div>
        </div>
      </div>

      {/* Экспертный вердикт с объяснимой цепочкой (низходящая модель) */}
      <VerdictBlock id={id} />

      {/* Восходящий агент: корреляции в сети (подход Palantir) */}
      <AgentBlock id={id} entityName={report.entity.name} onSelect={onSelect} />

      <div className="kpi-grid">
        <KpiCard label="Оценка риска" value={report.risk_score.toFixed(2)}
                 hint={<span className={`badge ${report.risk_level}`}>{LEVEL_LABEL[report.risk_level]}</span>} />
        <KpiCard label="Контрагентов" value={String(report.counterparties.length)} />
        <KpiCard label="Контрактов" value={String(totalContracts)} />
        <KpiCard label="Сумма контрактов" value={formatMoney(totalAmount)} />
      </div>

      {/* Графики вердикта: те же данные, что в таблицах — только форма */}
      <Section title="Графики вердикта" tip="Визуализация тех же данных, что в таблицах ниже: суммы по контрагентам, распределение сигналов, карта связей. График не добавляет и не меняет выводы — помогает увидеть масштаб">
        <div className="charts-grid">
          <div>
            <h4 className="chart-title">Суммы контрактов по контрагентам</h4>
            <AmountBars rows={report.counterparties} />
          </div>
          <div>
            <h4 className="chart-title">Сигналы по степени серьёзности</h4>
            <SignalsDonut signals={verdict?.signals ?? []} />
          </div>
          <div>
            <h4 className="chart-title">Карта связей (окружение сущности)</h4>
            <MiniGraph
              rows={report.counterparties}
              centerName={report.entity.name}
              onSelect={onSelect}
            />
          </div>
        </div>
      </Section>

      <FactorsBlock report={report} />

      <div className="card">
        <h3>Гипотеза для проверки</h3>
        <blockquote className="hypothesis"><Expandable text={report.hypothesis} limit={400} /></blockquote>
        <p className="muted">{report.data_note}</p>
        <p className="muted">Источники данных: {report.sources.map((s) => SOURCE_LABELS[s] ?? s).join(", ")}</p>
      </div>

      <CounterpartiesTable report={report} onSelect={onSelect} />

      {entityContracts.length > 0 && (
        <div className="card">
          <h3>Контракты сущности</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Номер</th><th>Дата</th><th>Контрагент</th>
                <th>Предмет</th><th className="num">Сумма</th><th>Проверка</th>
              </tr>
            </thead>
            <tbody>
              {entityContracts.slice(0, 10).map((c) => (
                <tr key={c.contract_number}>
                  <td className="mono">{c.contract_number}</td>
                  <td className="mono">{c.date}</td>
                  <td>
                    <button className="link" onClick={() => onSelect(c.customer.id === id ? c.supplier.id : c.customer.id)}>
                      {c.customer.id === id ? c.supplier.name : c.customer.name}
                    </button>
                  </td>
                  <td>{c.subject}</td>
                  <td className="num">{formatMoney(c.amount)}</td>
                  <td>
                    <span className={`badge ${c.severity === "high" ? "high" : c.severity === "medium" ? "medium" : "low"}`}>
                      {c.check_status.replace("_", " ")}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {entityContracts.length > 10 && <p className="muted small">Показано 10 из {entityContracts.length} — полный реестр в разделе «Контракты».</p>}
        </div>
      )}
    </div>
  );
}
