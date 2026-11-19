// Стартовая панель: сводка по системе, последние сигналы, быстрые переходы.
import { useQuery } from "@tanstack/react-query";
import { primarySource } from "../data/sources";
import { SEVERITY_LABELS, type Signal } from "../data/types";

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
  const { data: contracts } = useQuery({
    queryKey: ["contracts"], queryFn: () => primarySource().getContracts(),
  });

  const high = signals.filter((s) => s.severity === "high").length;
  const stats = [
    { label: "Сущностей в сети", value: overview?.entities_count ?? "—" },
    { label: "Связей (контрактов)", value: overview?.relations_count ?? contracts?.length ?? "—" },
    { label: "Сигналов", value: signals.length || "—", accent: signals.length > 0 },
    { label: "Высокой степени", value: high || "—", accent: high > 0, danger: high > 0 },
    { label: "Актов в нормативной базе", value: laws?.length ?? "—" },
  ];

  return (
    <div>
      <div className="card landing-hero">
        <h1>Аналитический контур профилактики коррупционных правонарушений</h1>
        <p className="muted">
          Гибрид низходящей экспертной системы и восходящего агента: правила выявляют
          известные схемы, агент находит связи в данных, нейросеть озвучивает выводы.
          Каждый сигнал объясним и ссылается на нормативный акт. Решение принимает человек.
        </p>
        <div className="landing-stats">
          {stats.map((s) => (
            <div className={`stat-tile ${s.danger ? "danger" : ""}`} key={s.label}>
              <div className="stat-value">{s.value}</div>
              <div className="stat-label">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="landing-section-head">
          <h3>Сигналы, требующие внимания</h3>
          <button className="link" onClick={onGoSignals}>Все сигналы →</button>
        </div>
        {!signals.length && <p className="muted">Сигналов нет. Начните с поиска организации слева.</p>}
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

      <div className="card">
        <h3>Как работать с системой</h3>
        <ol className="landing-steps">
          <li>Найдите организацию в поиске слева — откроется отчёт с вердиктом и графиками.</li>
          <li>Изучите цепочку объяснения: факты → признаки → правовые основания.</li>
          <li>Провалитесь по связям (таблица, мини-граф) — схемы редко ограничены одной организацией.</li>
          <li>Примите решение: «Подтвердить» или «Отклонить» — решение фиксируется в журнале.</li>
        </ol>
      </div>
    </div>
  );
}
