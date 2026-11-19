// Журнал решений сотрудника: каждый сигнал подтверждён или отклонён человеком.
import { useQuery } from "@tanstack/react-query";
import { primarySource } from "../data/sources";

export default function JournalPanel() {
  const { data } = useQuery({
    queryKey: ["decisions"],
    queryFn: () => primarySource().listDecisions(),
    refetchInterval: 15000,
  });

  return (
    <div className="panel">
      <h3>Журнал решений</h3>
      <p className="muted">Решение о сигнале всегда принимает человек.</p>
      {!data?.length && <p className="muted">Записей пока нет.</p>}
      <div className="journal-list">
        {data?.map((d) => (
          <div className="journal-item" key={d.id}>
            <div className="journal-head">
              <span className={`badge ${d.decision === "confirmed" ? "low" : "high"}`}>
                {d.decision === "confirmed" ? "Подтверждён" : "Отклонён"}
              </span>
              <span className="mono muted">сущность #{d.entity_id}</span>
            </div>
            {d.comment && <div className="journal-comment">{d.comment}</div>}
            <div className="muted small">{new Date(d.created_at).toLocaleString("ru-RU")}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
