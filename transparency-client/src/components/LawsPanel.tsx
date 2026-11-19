// Нормативная база: поиск по названию и содержанию, полные аннотации.
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { primarySource } from "../data/sources";

export default function LawsPanel() {
  const { data: laws, isLoading } = useQuery({
    queryKey: ["laws"],
    queryFn: () => primarySource().getLaws(),
  });
  const { data: providers } = useQuery({
    queryKey: ["legal-providers"],
    queryFn: () => primarySource().getLegalProviders(),
  });
  const [q, setQ] = useState("");

  const filtered = laws?.filter((l) => {
    const s = q.trim().toLowerCase();
    return !s || l.title.toLowerCase().includes(s) || l.annotation.toLowerCase().includes(s);
  });

  if (isLoading) return <div className="card skeleton">Загружаем нормативную базу…</div>;

  return (
    <div>
      <div className="card">
        <h3>Нормативная база</h3>
        <p className="muted">
          Законы, на которые ссылается экспертная система и агент. Ссылки на эти акты
          приводятся в каждом сигнале — сотрудник сразу видит правовое основание проверки.
        </p>
        <input
          className="input"
          placeholder="Поиск по названию или содержанию… (например: взятка, закупки, конфликт)"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <p className="muted small">Актов в базе: {laws?.length ?? 0}</p>
        {providers?.providers.map((p) => (
          <p className="muted small" key={p.id}>
            <span className={`badge ${p.status === "active" ? "low" : p.status === "configured" ? "medium" : "high"}`}>
              {p.status === "active" ? "активен" : p.status === "configured" ? "настроен" : "не настроен"}
            </span>{" "}
            {p.title}: {p.detail}
          </p>
        ))}
        <p className="muted small">
          Актуальные редакции:{" "}
          <a className="link" href="https://publication.pravo.gov.ru" target="_blank" rel="noreferrer">
            publication.pravo.gov.ru
          </a>
        </p>
      </div>
      {filtered?.map((law) => (
        <div className="card" key={law.id}>
          <h3>{law.title}</h3>
          <p className="muted">{law.annotation}</p>
          <p className="mono muted small">идентификатор: {law.id}</p>
        </div>
      ))}
      {filtered?.length === 0 && <div className="card">Ничего не найдено. Попробуйте другой запрос.</div>}
    </div>
  );
}
