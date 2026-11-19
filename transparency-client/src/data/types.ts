// Доменные типы приложения. UI работает только с ними —
// источник данных (сервер, будущие реестры) их маппит.

export type RiskLevel = "low" | "medium" | "high";

export interface EntitySummary {
  id: number;
  name: string;
  entity_type: string;
  external_id: string | null;
  attributes: Record<string, unknown>;
}

export interface Factor {
  name: string;
  value: number;
  contribution: number;
}

export interface CounterpartyRow {
  entity: EntitySummary;
  relation_types: string[];
  relation_count: number;
  total_amount: number;
  risk_score: number;
  risk_level: RiskLevel;
}

export interface Report {
  entity: EntitySummary;
  risk_score: number;
  risk_level: RiskLevel;
  factors: Factor[];
  hypothesis: string;
  data_note: string;
  counterparties: CounterpartyRow[];
  sources: string[];
  generated_at: string;
}

// ── Экспертная система ──
export interface Fact {
  name: string;
  value: string;
}

// Подобранная системой статья НПА (legal RAG: запрос из текста сигнала)
export interface ArticleMatch {
  id: string;
  act: string;
  act_title: string;
  article: string;
  title: string;
  excerpt: string;
  score: number;
}

export interface Indicator {
  rule: string;
  scheme: string;
  severity: "high" | "medium";
  description: string;
  law_refs: string[];
  action: string;        // что запросить у контрагента / какую проверку провести
  methodology: string;   // методическое основание (Минтруд / OCP / ГУСП)
  articles: ArticleMatch[];
}

export interface Signal extends Indicator {
  entity_id: number;
  entity_name: string;
  facts: Record<string, string>;
}

export type VerdictLevel = "critical" | "attention" | "normal";

export interface Verdict {
  entity_id: number;
  level: VerdictLevel;
  level_label: string;
  summary: string;
  recommendation: string;
  facts: Fact[];
  indicators: Indicator[];
  signals: Signal[];
  laws: string[];
}

export interface ContractRow {
  contract_number: string;
  date: string;
  amount: number;
  subject: string;
  customer: { id: number; name: string };
  supplier: { id: number; name: string };
  source: string;
  check_status: string; // "в_норме" | "средняя_степень" | "высокая_степень"
  severity: "none" | "medium" | "high";
}

export interface LegalProvider {
  id: string;
  title: string;
  status: string;
  detail: string;
}

export interface LawEntry {
  id: string;
  title: string;
  annotation: string;
}

// ── Модели LLM ──
export interface LLMSettings {
  provider: "offline" | "gigachat" | "ollama";
  ollama_url: string;
  ollama_model: string;
  gigachat_configured: boolean;
}

export interface LocalModel {
  name: string;
  size: number;
  modified_at: string;
}

export interface PullStatuses {
  pulls: Record<string, { status: string; detail?: string }>;
}

// ── Восходящий агент ──
export interface AgentFinding {
  type: string;
  description: string;
  related: string[];
  related_ids?: number[];
  facts?: Record<string, string>;
}

export interface AgentReport {
  narrative: string;
  findings: AgentFinding[];
  provider: string;
}

export interface AgentOverview extends AgentReport {
  entities_count: number;
  relations_count: number;
}

// ── Журнал решений ──
export type DecisionKind = "confirmed" | "rejected";

export interface Decision {
  id: number;
  entity_id: number;
  decision: DecisionKind;
  comment: string;
  created_at: string;
}

export interface NewDecision {
  entity_id: number;
  decision: DecisionKind;
  comment: string;
}

// ── Русские подписи (в интерфейсе только русский язык) ──
export const FACTOR_LABELS: Record<string, string> = {
  degree: "число связей",
  betweenness: "роль посредника в сети",
  contracts_count: "число контрактов",
  weight_ratio: "концентрация сумм (максимум к среднему)",
};

export const SOURCE_LABELS: Record<string, string> = {
  "fastapi-local": "Локальный сервер данных",
  procurement_mock: "Макет реестра закупок (синтетические данные)",
};

export const SEVERITY_LABELS: Record<string, string> = {
  high: "Высокая степень",
  medium: "Средняя степень",
};

export const VERDICT_LEVEL_LABELS: Record<VerdictLevel, string> = {
  critical: "Требует немедленной проверки",
  attention: "Повышенное внимание",
  normal: "В норме",
};
