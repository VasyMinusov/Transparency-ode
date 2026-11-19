// Графики аналитики: чистый SVG, без сторонних библиотек.
// Данные те же, что и в таблицах — визуализация ничего не добавляет и не меняет.
import type { CounterpartyRow, Signal } from "../data/types";

const COLORS = { low: "#34c77b", medium: "#f0a832", high: "#ef5350" } as const;

export function formatMoneyShort(v: number): string {
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)} млрд`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)} млн`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(0)} тыс.`;
  return `${v.toFixed(0)}`;
}

/** Горизонтальные бары: суммы контрактов по контрагентам (по убыванию суммы). */
export function AmountBars({ rows }: { rows: CounterpartyRow[] }) {
  const top = [...rows].sort((a, b) => b.total_amount - a.total_amount).slice(0, 8);
  const max = Math.max(...top.map((r) => r.total_amount), 1);
  const total = top.reduce((s, r) => s + r.total_amount, 0);
  if (!top.length) return <p className="muted">Нет данных для графика.</p>;
  return (
    <div className="chart">
      <div className="bar-row bar-head">
        <span className="bar-label" />
        <div className="bar-track head">
          <span className="bar-max mono">максимум: {formatMoneyShort(max)} ₽</span>
        </div>
        <span className="bar-value mono">доля</span>
      </div>
      {top.map((r) => (
        <div className="bar-row" key={r.entity.id}
             title={`${r.entity.name}
${formatMoneyShort(r.total_amount)} ₽ · риск ${r.risk_score.toFixed(2)}
клик — отчёт по сущности`}>
          <span className="bar-label">{r.entity.name}</span>
          <div className="bar-track">
            <div className="bar-fill" style={{
              width: `${(r.total_amount / max) * 100}%`,
              background: COLORS[r.risk_level],
            }} />
          </div>
          <span className="bar-value mono">
            {total > 0 ? `${Math.round((r.total_amount / total) * 100)}%` : "—"}
          </span>
        </div>
      ))}
      {rows.length > 8 && <p className="muted small">…и ещё {rows.length - 8} контрагентов в таблице ниже</p>}
    </div>
  );
}

/** Кольцевая диаграмма: сигналы по степени серьёзности. */
export function SignalsDonut({ signals }: { signals: Signal[] }) {
  const high = signals.filter((s) => s.severity === "high").length;
  const medium = signals.filter((s) => s.severity === "medium").length;
  const total = high + medium;
  const R = 44, C = 2 * Math.PI * R;
  const fracHigh = total ? high / total : 0;
  return (
    <div className="donut-wrap">
      <div className="donut-relative">
        <svg viewBox="0 0 120 120" className="donut">
          <circle cx="60" cy="60" r={R} fill="none" stroke="#1a2540" strokeWidth="15" />
          {high > 0 && (
            <circle cx="60" cy="60" r={R} fill="none" stroke={COLORS.high} strokeWidth="15"
                    strokeDasharray={`${fracHigh * C} ${C}`} transform="rotate(-90 60 60)" />
          )}
          {medium > 0 && (
            <circle cx="60" cy="60" r={R} fill="none" stroke={COLORS.medium} strokeWidth="15"
                    strokeDasharray={`${(1 - fracHigh) * C} ${C}`}
                    strokeDashoffset={-fracHigh * C} transform="rotate(-90 60 60)" />
          )}
        </svg>
        <div className="donut-center">
          <div className="donut-num">{total}</div>
          <div className="muted small">{total === 1 ? "сигнал" : total < 5 && total > 0 ? "сигнала" : "сигналов"}</div>
        </div>
      </div>
      <div className="donut-legend">
        <span><i style={{ background: COLORS.high }} /> высокая: {high}</span>
        <span><i style={{ background: COLORS.medium }} /> средняя: {medium}</span>
      </div>
    </div>
  );
}

/** Мини-граф связей: центральная сущность и окружение (до 10 узлов — читаемо). */
export function MiniGraph({ rows, centerName, onSelect }: {
  rows: CounterpartyRow[]; centerName: string; onSelect: (id: number) => void;
}) {
  const top = rows.slice(0, 10);
  const W = 340, H = 270, CX = W / 2, CY = H / 2 - 6;
  const maxAmount = Math.max(...top.map((r) => r.total_amount), 1);
  if (!top.length) return <p className="muted">Связей нет.</p>;
  const pos = (i: number) => {
    const angle = (2 * Math.PI * i) / top.length - Math.PI / 2;
    return { x: CX + 108 * Math.cos(angle), y: CY + 96 * Math.sin(angle) };
  };
  return (
    <div className="minigraph-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} className="minigraph">
        {top.map((r, i) => {
          const p = pos(i);
          return (
            <line key={`e${r.entity.id}`} x1={CX} y1={CY} x2={p.x} y2={p.y}
                  stroke="#3b82f6" strokeWidth={1 + 3.5 * (r.total_amount / maxAmount)}
                  strokeOpacity={0.5} />
          );
        })}
        {top.map((r, i) => {
          const p = pos(i);
          const name = r.entity.name.length > 13 ? r.entity.name.slice(0, 12) + "…" : r.entity.name;
          return (
            <g key={`n${r.entity.id}`} onClick={() => onSelect(r.entity.id)} className="mg-node">
              <circle cx={p.x} cy={p.y} r={9 + 7 * r.risk_score} fill={COLORS[r.risk_level]}
                      stroke="#0b1220" strokeWidth={2}>
                <title>{`${r.entity.name}
риск ${r.risk_score.toFixed(2)} · ${formatMoneyShort(r.total_amount)} ₽
клик — отчёт`}</title>
              </circle>
              <text x={p.x} y={p.y + 22} textAnchor="middle" className="mg-label">{name}</text>
            </g>
          );
        })}
        <circle cx={CX} cy={CY} r={25} fill="#4c8dff" stroke="#0b1220" strokeWidth={2} />
        <text x={CX} y={CY + 44} textAnchor="middle" className="mg-center-label">
          {centerName.length > 24 ? centerName.slice(0, 23) + "…" : centerName}
        </text>
        {rows.length > 10 && (
          <text x={CX} y={H - 4} textAnchor="middle" className="mg-more">
            +{rows.length - 10} ещё — полный список в таблице ниже
          </text>
        )}
      </svg>
      <div className="mg-legend muted small">
        размер узла — риск · толщина линии — сумма контрактов · цвет — степень риска
      </div>
    </div>
  );
}
