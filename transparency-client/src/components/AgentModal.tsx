// Модальное окно «Восходящий анализ сети»: сводка + визуализации + структурированные находки.
import { useEffect } from "react";
import type { AgentFinding } from "../data/types";

const TYPE_LABELS: Record<string, string> = {
  кластер_адресов: "Кластер общего адреса",
  пересечение_сигналов: "Системность признака",
  концентрация_потоков: "Узел-посредник",
  сетевой_кластер: "Сетевой кластер",
  узлы_сети: "Ключевые узлы",
};
const TYPE_COLORS = ["#4c8dff", "#f0a832", "#ef5350", "#34c77b", "#a78bfa"];

function Donut({ byType }: { byType: Record<string, number> }) {
  const entries = Object.entries(byType);
  const total = entries.reduce((s, e) => s + e[1], 0);
  const R = 44, C = 2 * Math.PI * R;
  let offset = 0;
  return (
    <div className="donut-wrap">
      <div className="donut-relative">
        <svg viewBox="0 0 120 120" className="donut">
          <circle cx="60" cy="60" r={R} fill="none" stroke="#1a2540" strokeWidth="15" />
          {entries.map(([type, n], i) => {
            const frac = n / (total || 1);
            const el = (
              <circle key={type} cx="60" cy="60" r={R} fill="none"
                      stroke={TYPE_COLORS[i % TYPE_COLORS.length]} strokeWidth="15"
                      strokeDasharray={`${frac * C} ${C}`} strokeDashoffset={-offset * C}
                      transform="rotate(-90 60 60)">
                <title>{TYPE_LABELS[type] ?? type}: {n}</title>
              </circle>
            );
            offset += frac;
            return el;
          })}
        </svg>
        <div className="donut-center">
          <div className="donut-num">{total}</div>
          <div className="muted small">корреляций</div>
        </div>
      </div>
      <div className="donut-legend col">
        {entries.map(([type, n], i) => (
          <span key={type}><i style={{ background: TYPE_COLORS[i % TYPE_COLORS.length] }} />{TYPE_LABELS[type] ?? type}: {n}</span>
        ))}
      </div>
    </div>
  );
}

function SchemeBars({ findings }: { findings: AgentFinding[] }) {
  const rows = findings
    .filter((f) => f.type === "пересечение_сигналов" && f.facts?.["схема"])
    .map((f) => ({ scheme: f.facts!["схема"], n: Number(f.facts!["число_сущностей"] || f.related.length) }))
    .sort((a, b) => b.n - a.n)
    .slice(0, 7);
  if (!rows.length) return <p className="muted">Нет пересечений признаков.</p>;
  const max = Math.max(...rows.map((r) => r.n), 1);
  return (
    <div className="chart">
      {rows.map((r) => (
        <div className="bar-row" key={r.scheme}>
          <span className="bar-label">{r.scheme}</span>
          <div className="bar-track"><div className="bar-fill" style={{ width: `${(r.n / max) * 100}%` }} /></div>
          <span className="bar-value mono">{r.n}</span>
        </div>
      ))}
      <p className="muted small">Сколько связанных сущностей имеют каждый признак</p>
    </div>
  );
}

export default function AgentModal({ entityName, findings, narrative, onClose, onOpenEntity }: {
  entityName: string;
  findings: AgentFinding[];
  narrative: string;
  onClose: () => void;
  onOpenEntity: (id: number) => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const byType: Record<string, number> = {};
  findings.forEach((f) => { byType[f.type] = (byType[f.type] || 0) + 1; });
  const clusters = findings.filter((f) => f.type.includes("кластер"));

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <h2>Восходящий анализ сети</h2>
            <p className="muted">окружение сущности «{entityName}» · {findings.length} корреляций</p>
          </div>
          <button className="btn ghost" onClick={onClose}>✕</button>
        </div>

        <p className="agent-narrative modal-narrative">{narrative}</p>

        <div className="modal-grid">
          <div className="card">
            <h3>Типы корреляций</h3>
            <Donut byType={byType} />
          </div>
          <div className="card">
            <h3>Признаки по охвату</h3>
            <SchemeBars findings={findings} />
          </div>
        </div>

        {clusters.length > 0 && (
          <div className="card">
            <h3>Кластеры</h3>
            <p className="muted">Группы организаций, объединённых общим адресом. Клик по организации — её отчёт.</p>
            {clusters.map((f, i) => (
              <div className="cluster-card" key={i}>
                <div className="chips-row">
                  {(f.related_ids ?? []).map((id, j) => (
                    <button className="chip chip-btn" key={id}
                            onClick={() => { onClose(); onOpenEntity(id); }}>
                      {f.related[j] ?? id}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="card">
          <h3>Все корреляции</h3>
          <div className="findings-list">
            {findings.map((f, i) => (
              <div className="finding-row" key={i}>
                <span className="chip">{TYPE_LABELS[f.type] ?? f.type}</span>
                <p className="finding-text">{f.description}</p>
                {(f.related_ids ?? []).length > 0 && (
                  <div className="chips-row">
                    {f.related_ids!.map((id, j) => (
                      <button className="chip chip-btn" key={id}
                              onClick={() => { onClose(); onOpenEntity(id); }}>
                        {f.related[j] ?? id}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
          <p className="muted small">Корреляции — гипотезы для проверки человеком, не выводы о нарушениях.</p>
        </div>
      </div>
    </div>
  );
}
