// Лента сигналов: сгруппирована по сущностям, сортировка — степень серьёзности.
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { primarySource } from "../data/sources";
import { SEVERITY_LABELS, type Signal } from "../data/types";
import Expandable from "./Expandable";
import LegalArticles from "./LegalArticles";

export default function SignalsPanel({ onOpenEntity }: { onOpenEntity: (id: number) => void }) {
  const { data: signals, isLoading } = useQuery({
    queryKey: ["signals"],
    queryFn: () => primarySource().getSignals(),
    refetchInterval: 30000,
  });
  const { data: overview } = useQuery({
    queryKey: ["agent-overview"],
    queryFn: () => primarySource().getAgentOverview(),
  });
  const { data: decisions } = useQuery({
    queryKey: ["decisions"],
    queryFn: () => primarySource().listDecisions(),
  });
  const [showNetwork, setShowNetwork] = useState(false);
  // Сигналы по сущностям с решением «отклонён» не исчезают — помечаются и остаются в ленте
  const rejectedIds = new Set(
    decisions?.filter((d) => d.decision === "rejected").map((d) => d.entity_id) ?? []
  );

  if (isLoading) return <div className="card skeleton">Формируем ленту сигналов…</div>;
  if (!signals?.length) return <div className="card">Признаков коррупционных схем не выявлено.</div>;

  return (
    <div>
      <div className="card">
        <h3>Лента сигналов</h3>
        <p className="muted">
          Каждый сигнал — результат срабатывания правила экспертной системы.
          Нажмите «?» рядом с разделом, чтобы увидеть пояснение.
        </p>
        {overview && (
          <div className="network-summary">
            <button className="link" onClick={() => setShowNetwork((v) => !v)}>
              {showNetwork ? "Скрыть сводку агента по сети" : "Сводка агента по сети: узлы и кластеры риска"}
            </button>
            {showNetwork && (
              <>
                <p className="agent-narrative">{overview.narrative}</p>
                <p className="muted small">
                  Сущностей в сети: {overview.entities_count}, связей: {overview.relations_count}.
                  Корреляции — гипотезы для проверки человеком.
                </p>
              </>
            )}
          </div>
        )}
      </div>
      {signals.map((s, i) => (
        <SignalCard key={`${s.entity_id}-${s.rule}-${i}`} signal={s} onOpen={onOpenEntity}
                    rejected={rejectedIds.has(s.entity_id)} />
      ))}
      {rejectedIds.size > 0 && (
        <p className="muted small">Сигналы по {rejectedIds.size} сущностям отклонены сотрудником — они сохранены и остаются в ленте для истории.</p>
      )}
    </div>
  );
}

function SignalCard({ signal: s, onOpen, rejected }: { signal: Signal; onOpen: (id: number) => void; rejected?: boolean }) {
  const { data: laws } = useQuery({ queryKey: ["laws"], queryFn: () => primarySource().getLaws() });
  const lawTitle = (id: string) => laws?.find((l) => l.id === id)?.title ?? id;
  return (
    <div className={`card signal ${s.severity === "high" ? "signal-high" : ""} ${rejected ? "signal-rejected" : ""}`}>
      <div className="signal-head">
        <span className={`badge ${s.severity === "high" ? "high" : "medium"}`}>
          {SEVERITY_LABELS[s.severity]}
        </span>
        {rejected && (
          <span className="badge low" data-tip="Сигнал отклонён сотрудником, сохранён для истории">
            отклонён сотрудником
          </span>
        )}
        <button className="link" onClick={() => onOpen(s.entity_id)} data-tip="Открыть отчёт и вердикт по сущности">
          {s.entity_name}
        </button>
      </div>
      <div className="signal-scheme">{s.scheme}</div>
      <p className="muted"><Expandable text={s.description} limit={260} /></p>
      <p className="methodology-line">Методическое основание: {s.methodology}</p>
      <LegalArticles articles={s.articles} />
      <div className="chips-row">
        {s.law_refs.map((law) => (
          <span className="chip" key={law} data-tip={lawTitle(law)}>{law}</span>
        ))}
      </div>
    </div>
  );
}
