// Слой абстракции над источниками данных.
//
// Чтобы подключить новый реестр (zakupki.gov.ru, кадровый реестр, декларации):
// 1. Реализуйте TransparencySource для него.
// 2. Добавьте экземпляр в SOURCES ниже.
// Интерфейс менять не нужно — он работает с доменными типами, а не с конкретным сервером.
import type {
  AgentOverview, AgentReport, ContractRow, Decision, EntitySummary, LawEntry,
  LLMSettings, LegalProvider, LocalModel, NewDecision, PullStatuses, Report, Signal, Verdict,
  GraphPayload,
} from "./types";
import { httpSource } from "./httpSource";

export interface TransparencySource {
  /** Стабильный идентификатор источника */
  readonly id: string;
  /** Название для интерфейса */
  readonly title: string;
  /** Поиск сущностей по названию / ИНН */
  searchEntities(query: string): Promise<EntitySummary[]>;
  /** Аналитический отчёт по сущности */
  getReport(entityId: number): Promise<Report>;
  /** Экспертный вердикт по сущности (цепочка: факты → признаки → сигналы → вердикт) */
  getVerdict(entityId: number): Promise<Verdict>;
  /** Лента сигналов по всем сущностям */
  getSignals(): Promise<Signal[]>;
  /** Реестр контрактов (по мере подключения реестров — полнота растёт) */
  getContracts(): Promise<ContractRow[]>;
  /** Нормативно-правовая база */
  getLaws(): Promise<LawEntry[]>;
  /** Восходящий агент: корреляции в сети по сущности */
  getAgentReport(entityId: number): Promise<AgentReport>;
  /** Восходящий агент: сводка по всей сети */
  getAgentOverview(): Promise<AgentOverview>;
  /** Граф всей сети для визуализации */
  getGraph(): Promise<GraphPayload>;
  /** Настройки LLM */
  getLLMSettings(): Promise<LLMSettings>;
  setLLMSettings(s: LLMSettings): Promise<LLMSettings>;
  /** Провайдеры правового слоя */
  getLegalProviders(): Promise<{ providers: LegalProvider[] }>;
  /** Локальные модели (Ollama) */
  getLocalModels(): Promise<{ models: LocalModel[] }>;
  pullModel(model: string): Promise<{ model: string; status: string }>;
  getPullStatuses(): Promise<PullStatuses>;
  deleteModel(name: string): Promise<{ deleted: string }>;
  /** Журнал решений сотрудника */
  listDecisions(): Promise<Decision[]>;
  /** Записать решение сотрудника (человек в контуре) */
  submitDecision(d: NewDecision): Promise<Decision>;
}

const SOURCES: TransparencySource[] = [
  httpSource,
  // будущие реестры: закупки, кадры, декларации — та же реализация контракта
];

export function getSources(): readonly TransparencySource[] {
  return SOURCES;
}

/**
 * Основной источник для интерфейса.
 * Когда подключится несколько реестров, здесь появится композит:
 * параллельные запросы + слияние ответов в один доменный результат.
 */
export function primarySource(): TransparencySource {
  return SOURCES[0];
}
