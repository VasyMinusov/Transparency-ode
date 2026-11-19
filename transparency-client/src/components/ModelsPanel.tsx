// Управление локальными моделями: просмотр, скачивание, удаление, выбор активной.
// Работает через Ollama (ollama serve); без Ollama — понятное сообщение.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { primarySource } from "../data/sources";
import type { LLMSettings, LocalModel } from "../data/types";

const PROVIDERS: { id: LLMSettings["provider"]; label: string; tip: string }[] = [
  { id: "offline",  label: "Детерминированный режим",
    tip: "Без нейросети: текст формируется шаблоном. Полностью воспроизводимо, работает всегда" },
  { id: "ollama",   label: "Локальная модель (Ollama)",
    tip: "Нейросеть работает на этом компьютере через Ollama. Данные не покидают контур" },
  { id: "gigachat", label: "GigaChat (облако)",
    tip: "Отечественная облачная модель. Требует credentials на сервере (APP_GIGACHAT_CREDENTIALS)" },
];

function formatSize(bytes?: number): string {
  if (!bytes) return "—";
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} ГБ`;
  return `${(bytes / 1e6).toFixed(0)} МБ`;
}

export default function ModelsPanel() {
  const qc = useQueryClient();
  const { data: settings, isLoading } = useQuery({
    queryKey: ["llm-settings"],
    queryFn: () => primarySource().getLLMSettings(),
  });
  const { data: models, error: modelsError, isFetching: modelsLoading } = useQuery({
    queryKey: ["local-models"],
    queryFn: () => primarySource().getLocalModels(),
    retry: false,
    refetchInterval: 15000,
  });
  const { data: pulls } = useQuery({
    queryKey: ["model-pulls"],
    queryFn: () => primarySource().getPullStatuses(),
    refetchInterval: 3000,
  });

  const [pullName, setPullName] = useState("");
  const saveMutation = useMutation({
    mutationFn: (s: LLMSettings) => primarySource().setLLMSettings(s),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["llm-settings"] });
      qc.invalidateQueries({ queryKey: ["agent"] });
      qc.invalidateQueries({ queryKey: ["agent-overview"] });
    },
  });
  const pullMutation = useMutation({
    mutationFn: (model: string) => primarySource().pullModel(model),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["model-pulls"] }); setPullName(""); },
  });
  const deleteMutation = useMutation({
    mutationFn: (name: string) => primarySource().deleteModel(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["local-models"] }),
  });

  if (isLoading) return <div className="card skeleton">Загружаем настройки…</div>;

  const ollamaDown = !!modelsError;
  const activeModel = settings?.provider === "ollama" ? settings.ollama_model : null;

  return (
    <div>
      <div className="card">
        <h3>Модель озвучивания агента</h3>
        <p className="muted">
          Агент озвучивает найденные корреляции выбранной моделью. Данные анализа
          (факты и сигналы) всегда формируются детерминированно — модель формулирует только текст.
        </p>
        <div className="provider-grid">
          {PROVIDERS.map((p) => (
            <button
              key={p.id}
              className={`provider-card ${settings?.provider === p.id ? "active" : ""}`}
              disabled={saveMutation.isPending}
              onClick={() => settings && saveMutation.mutate({ ...settings, provider: p.id })}
              data-tip={p.tip}
            >
              <b>{p.label}</b>
              {settings?.provider === p.id && <span className="badge low">активна</span>}
            </button>
          ))}
        </div>
        {settings?.provider === "gigachat" && !settings.gigachat_configured && (
          <p className="rejected-note">GigaChat не настроен: задайте APP_GIGACHAT_CREDENTIALS на сервере.</p>
        )}
      </div>

      <div className="card">
        <h3>Локальные модели (Ollama)</h3>
        {ollamaDown && (
          <p className="rejected-note">
            Ollama не запущен. Установите Ollama и выполните «ollama serve» —
            тогда здесь появятся локальные модели. Сейчас работает детерминированный режим.
          </p>
        )}
        {!ollamaDown && (
          <table className="table">
            <thead>
              <tr><th>Модель</th><th className="num">Размер</th><th>Изменена</th><th></th></tr>
            </thead>
            <tbody>
              {models?.models.map((m: LocalModel) => (
                <tr key={m.name}>
                  <td className="mono">{m.name} {m.name === activeModel && <span className="badge low">активна</span>}</td>
                  <td className="num">{formatSize(m.size)}</td>
                  <td className="muted">{m.modified_at ? new Date(m.modified_at).toLocaleDateString("ru-RU") : "—"}</td>
                  <td className="num">
                    {m.name !== activeModel && settings && (
                      <button className="link" onClick={() => saveMutation.mutate(
                        { ...settings, provider: "ollama", ollama_model: m.name })}>
                        сделать активной
                      </button>
                    )}{" "}
                    <button className="link danger-link" onClick={() => deleteMutation.mutate(m.name)}>
                      удалить
                    </button>
                  </td>
                </tr>
              ))}
              {models?.models.length === 0 && <tr><td colSpan={4} className="muted">Моделей нет — скачайте первую ниже.</td></tr>}
            </tbody>
          </table>
        )}
        <div className="pull-row">
          <input
            className="input"
            placeholder="Скачать модель, например: llama3.1:8b или qwen2.5:7b"
            value={pullName}
            onChange={(e) => setPullName(e.target.value)}
          />
          <button className="btn" disabled={!pullName.trim() || ollamaDown}
                  onClick={() => pullMutation.mutate(pullName.trim())}>
            Скачать
          </button>
        </div>
        {pulls && Object.entries(pulls.pulls).length > 0 && (
          <div className="pull-statuses">
            {Object.entries(pulls.pulls).map(([name, st]) => (
              <p className="muted small" key={name}>
                {name}: {st.status === "running" ? "скачивание…" : st.status === "done" ? "готова" : `ошибка (${st.detail})`}
              </p>
            ))}
          </div>
        )}
        {modelsLoading && <p className="muted small">Обновляем список…</p>}
      </div>
    </div>
  );
}
