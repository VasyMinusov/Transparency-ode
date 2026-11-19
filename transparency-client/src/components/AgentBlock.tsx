// Восходящий агент: компактная сводка в отчёте; полный интерактив — в модальном окне.
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { primarySource } from "../data/sources";
import AgentModal from "./AgentModal";
import Expandable from "./Expandable";

const PROVIDER_LABELS: Record<string, string> = {
  offline: "детерминированный режим (без языковой модели)",
  gigachat: "нейросеть GigaChat",
  ollama: "локальная нейросеть (Ollama)",
};

const TYPE_LABELS: Record<string, string> = {
  кластер_адресов: "кластеры адресов",
  пересечение_сигналов: "системные признаки",
  концентрация_потоков: "узлы-посредники",
  сетевой_кластер: "сетевые кластеры",
  узлы_сети: "ключевые узлы",
};

export default function AgentBlock({ id, entityName, onSelect }: {
  id: number; entityName: string; onSelect: (id: number) => void;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["agent", id],
    queryFn: () => primarySource().getAgentReport(id),
  });
  const [open, setOpen] = useState(false);

  if (isLoading) return <div className="card skeleton">Восходящий агент исследует сеть…</div>;
  if (!data) return null;

  const byType: Record<string, number> = {};
  data.findings.forEach((f) => { byType[f.type] = (byType[f.type] || 0) + 1; });

  return (
    <div className="card agent">
      <h3>
        Восходящий анализ сети
        <span className="tip" data-tip="Агент идёт от данных вверх: ищет корреляции, которые не зашиты в правила (кластеры адресов, пересечения сигналов, узлы-посредники). Текст озвучивает нейросеть: локальная (Ollama) или GigaChat; если модель недоступна — работает детерминированный шаблон">?</span>
      </h3>
      <p className="agent-narrative"><Expandable text={data.narrative} limit={200} /></p>
      <div className="chips-row agent-summary-chips">
        <span className="chip">корреляций: {data.findings.length}</span>
        {Object.entries(byType).map(([type, n]) => (
          <span className="chip" key={type}>{TYPE_LABELS[type] ?? type}: {n}</span>
        ))}
      </div>
      <div className="agent-actions">
        <button className="btn" onClick={() => setOpen(true)}>
          Открыть интерактивный анализ
        </button>
        <span className="muted small">Озвучивание: {PROVIDER_LABELS[data.provider] ?? data.provider}</span>
      </div>
      {open && (
        <AgentModal entityName={entityName} findings={data.findings} narrative={data.narrative}
                    onClose={() => setOpen(false)} onOpenEntity={onSelect} />
      )}
    </div>
  );
}
