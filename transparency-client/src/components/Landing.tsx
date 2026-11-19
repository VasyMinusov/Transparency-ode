// Стартовая панель: дашборд с живыми метриками, распределением рисков,
// топ-5 рискованных сущностей и последними сигналами.
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { primarySource } from "../data/sources";
import { SEVERITY_LABELS, type Signal } from "../data/types";

// Анимированный счётчик: плавно считает от 0 до target за 900 мс.
function AnimatedNumber({ value }: { value: number }) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    if (!value) { setDisplay(0); return; }
    const start = performance.now();
    const duration = 900;
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(Math.round(value * eased));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return <>{display}</>;
}

const COLORS = { low: "#34c77b", medium: "#f0a832", high: "#ef5350" };

export default function Landing({
  signals, onOpenEntity, onGoSignals,
}: {
  signals: Signal[];
  onOpenEntity: (id: number) => void;
  onGoSignals: () => void;
}) {
  const { data: overview } = useQuery({
    queryKey: ["agent-overview"],
    queryFn: () => primarySource().getAgentOverview(),
  });
  const { data: laws } = useQuery({ queryKey: ["laws"], queryFn: () => primarySource().getLaws() });
  const { data: graph } = useQuery({
    queryKey: ["network-graph"],
    queryFn: () => primarySource().getGraph(),
  });

  const high = signals.filter((s) => s.severity === "high").length;
  const medium = signals.filter((s) => s.severity === "medium").length;
  const total = high + medium;

  // Топ-5 самых рискованных сущностей из графа
  const topRisky = (graph?.nodes ?? [])
    .slice()
    .sort((a, b) => b.risk_score - a.risk_score)
    .slice(0, 5);

  // Donut: распределение рисков по всей сети
  const riskCounts = { low: 0, medium: 0, high: 0 };
  (graph?.nodes ?? []).forEach((n) => riskCounts[n.risk_level]++);
  const totalNodes = riskCounts.low + riskCounts.medium + riskCounts.high;
  const R = 54, C = 2 * Math.PI * R;
  let offset = 0;
  const donutSegments = (["high", "medium", "low"] as const).map((lvl) => {
    const frac = totalNodes ? riskCounts[lvl] / totalNodes : 0;
    const seg = { lvl, frac, offset };
    offset += frac;
    return seg;
  });

  return (
    <div>
      <div className="card landing-hero">
        <h1>Аналитический контур профилактики коррупционных правонарушений</h1>
        <p className="muted">
          Гибрид низходящей экспертной системы и восходящего агента: правила выявляют
          известные схемы, агент находит связи в данных, нейросеть озвучивает выводы.
          Каждый сигнал объясним и ссылается на нормативный акт. Решение принимает человек.
        </p>
      </div>

      {/* KPI-плитки с анимированными счётчиками */}
      <div className="dash-kpi-grid">
        <div className="dash-kpi">
          <div className="dash-kpi-value"><AnimatedNumber value={overview?.entities_count ?? 0} /></div>
          <div className="dash-kpi-label">сущностей в сети</div>
        </div>
        <div className="dash-kpi">
          <div className="dash-kpi-value"><AnimatedNumber value={overview?.relations_count ?? 0} /></div>
          <div className="dash-kpi-label">связей (контрактов)</div>
        </div>
        <div className="dash-kpi danger">
          <div className="dash-kpi-value"><AnimatedNumber value={total} /></div>
          <div className="dash-kpi-label">сигналов выявлено</div>
        </div>
        <div className="dash-kpi danger">
          <div className="dash-kpi-value"><AnimatedNumber value={high} /></div>
          <div className="dash-kpi-label">высокой степени</div>
        </div>
        <div className="dash-kpi">
          <div className="dash-kpi-value"><AnimatedNumber value={laws?.length ?? 0} /></div>
          <div className="dash-kpi-label">актов в нормативной базе</div>
        </div>
      </div>

      {/* Второй ряд: распределение рисков + топ-5 */}
      <div className="dash-row">
        <div className="card">
          <h3>Распределение рисков по сети</h3>
          <div className="dash-donut-wrap">
            <svg viewBox="0 0 140 140" className="dash-donut">
              <circle cx="70" cy="70" r={R} fill="none" stroke="#1a2540" strokeWidth="18" />
              {donutSegments.map((s) => s.frac > 0 && (
                <circle
                  key={s.lvl}
                  cx="70" cy="70" r={R}
                  fill="none"
                  stroke={COLORS[s.lvl]}
                  strokeWidth="18"
                  strokeDasharray={`${s.frac * C} ${C}`}
                  strokeDashoffset={-s.offset * C}
                  transform="rotate(-90 70 70)"
                />
              ))}
            </svg>
            <div className="dash-donut-center">
              <div className="dash-donut-num">{totalNodes}</div>
              <div className="muted small">сущностей</div>
            </div>
          </div>
          <div className="dash-donut-legend">
            <span><i style={{ background: COLORS.high }} /> высокая: {riskCounts.high}</span>
            <span><i style={{ background: COLORS.medium }} /> средняя: {riskCounts.medium}</span>
            <span><i style={{ background: COLORS.low }} /> низкая: {riskCounts.low}</span>
          </div>
        </div>

        <div className="card">
          <h3>Топ-5 сущностей по оценке риска</h3>
          {!topRisky.length && <p className="muted">Нет данных.</p>}
          <div className="dash-top-list">
            {topRisky.map((n, i) => (
              <button key={n.id} className="dash-top-row" onClick={() => onOpenEntity(n.id)}>
                <span className="dash-top-rank">#{i + 1}</span>
                <span className="dash-top-name">{n.name}</span>
                <span className="dash-top-bar-wrap">
                  <span
                    className="dash-top-bar"
                    style={{
                      width: `${n.risk_score * 100}%`,
                      background: COLORS[n.risk_level],
                    }}
                  />
                </span>
                <span className="dash-top-score mono">{n.risk_score.toFixed(2)}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Последние сигналы */}
      <div className="card">
        <div className="landing-section-head">
          <h3>Сигналы, требующие внимания</h3>
          <button className="link" onClick={onGoSignals}>Все сигналы →</button>
        </div>
        {!signals.length && <p className="muted">Сигналов нет. Начните с поиска организации.</p>}
        {signals.slice(0, 5).map((s, i) => (
          <div className="landing-signal" key={`${s.entity_id}-${s.rule}-${i}`}>
            <span className={`badge ${s.severity === "high" ? "high" : "medium"}`}>
              {SEVERITY_LABELS[s.severity]}
            </span>
            <button className="link" onClick={() => onOpenEntity(s.entity_id)}>{s.entity_name}</button>
            <span className="muted"> — {s.scheme}</span>
          </div>
        ))}
      </div>
    </div>
  );
}