// Поиск сущностей по названию / ИНН. Результат — кликабельный список.
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { primarySource } from "../data/sources";

export default function SearchPanel({ onSelect }: { onSelect: (id: number) => void }) {
  const [query, setQuery] = useState("");
  const { data, isFetching } = useQuery({
    queryKey: ["search", query],
    queryFn: () => primarySource().searchEntities(query),
    enabled: query.trim().length > 1,
    placeholderData: (prev) => prev,
  });

  return (
    <div className="panel">
      <h3>Поиск сущности</h3>
      <input
        className="input"
        placeholder="Название или ИНН…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div className="search-results">
        {query.trim().length <= 1 && (
          <p className="muted">Введите не менее 2 символов. Например: «Поставщик» или «7702».</p>
        )}
        {isFetching && <p className="muted">Поиск…</p>}
        {data?.length === 0 && <p className="muted">Ничего не найдено.</p>}
        {data?.map((e) => (
          <button className="search-item" key={e.id} onClick={() => onSelect(e.id)}>
            <span className="search-item-name">{e.name}</span>
            <span className="mono muted">{e.external_id ?? "—"}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
