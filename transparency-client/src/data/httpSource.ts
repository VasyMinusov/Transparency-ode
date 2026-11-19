// Реализация TransparencySource поверх локального сервера (FastAPI).
// Единственное место, где знают про HTTP и формат сервера.
import type { TransparencySource } from "./sources";
import type {
  AgentOverview, AgentReport, ContractRow, Decision, EntitySummary, LawEntry,
  LLMSettings, LegalProvider, LocalModel, NewDecision, PullStatuses, Report, Signal, Verdict,
  GraphPayload,
} from "./types";

const BASE = "http://127.0.0.1:8000/api/v1";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, init);
  if (!resp.ok) throw new Error(`${path}: HTTP ${resp.status}`);
  return resp.json() as Promise<T>;
}

export const httpSource: TransparencySource = {
  id: "fastapi-local",
  title: "Локальный сервер данных",

  searchEntities: (query: string) =>
    req<EntitySummary[]>(`/entities?q=${encodeURIComponent(query)}`),

  getReport: (entityId: number) => req<Report>(`/entities/${entityId}/report`),

  getVerdict: (entityId: number) => req<Verdict>(`/entities/${entityId}/verdict`),

  getSignals: () => req<Signal[]>("/signals"),

  getContracts: () => req<ContractRow[]>("/contracts"),

  getLaws: () => req<LawEntry[]>("/laws"),

  getAgentReport: (entityId: number) => req<AgentReport>(`/entities/${entityId}/agent-report`),

  getAgentOverview: () => req<AgentOverview>("/agent/overview"),

  getGraph: () => req<GraphPayload>("/graph"),

  getLLMSettings: () => req<LLMSettings>("/settings/llm"),

  setLLMSettings: (s: LLMSettings) =>
    req<LLMSettings>("/settings/llm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider: s.provider, ollama_url: s.ollama_url, ollama_model: s.ollama_model,
      }),
    }),

  getLegalProviders: () => req<{ providers: LegalProvider[] }>("/legal/providers"),

  getLocalModels: () => req<{ models: LocalModel[] }>("/settings/llm/models"),

  pullModel: (model: string) =>
    req<{ model: string; status: string }>("/settings/llm/models/pull", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model }),
    }),

  getPullStatuses: () => req<PullStatuses>("/settings/llm/models/pulls"),

  deleteModel: (name: string) =>
    req<{ deleted: string }>(`/settings/llm/models/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),

  listDecisions: () => req<Decision[]>("/decisions"),

  submitDecision: (d: NewDecision) =>
    req<Decision>("/decisions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(d),
    }),
};
