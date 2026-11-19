// Экспертный вердикт с цепочкой объяснения (низходящая модель):
// Факты → Признаки → Сигналы → Вердикт. Каждый шаг раскрыт и прокомментирован.
import { useQuery } from "@tanstack/react-query";
import { primarySource } from "../data/sources";
import Expandable from "./Expandable";
import LegalArticles from "./LegalArticles";
import { SEVERITY_LABELS, VERDICT_LEVEL_LABELS, type Verdict } from "../data/types";

function Tip({ text }: { text: string }) {
  return <span className="tip" data-tip={text}>?</span>;
}

export default function VerdictBlock({ id }: { id: number }) {
  const { data: verdict, isLoading } = useQuery({
    queryKey: ["verdict", id],
    queryFn: () => primarySource().getVerdict(id),
  });
  const { data: decisions } = useQuery({
    queryKey: ["decisions"],
    queryFn: () => primarySource().listDecisions(),
  });
  const latest = decisions?.find((d) => d.entity_id === id);

  if (isLoading) return <div className="card skeleton">Экспертная система анализирует…</div>;
  if (!verdict) return null;

  const levelClass = verdict.level === "critical" ? "high" : verdict.level === "attention" ? "medium" : "low";

  return (
    <div className="card verdict">
      {/* Этап 4 резюмирует цепочку — показываем вердикт первым, раскрытие ниже */}
      <div className="verdict-head">
        <div>
          <h3>
            Экспертный вердикт
            <Tip text="Итог работы правил экспертной системы: от знаний о коррупционных схемах — к проверке фактов. Не обвинение, а основание для проверки человеком" />
          </h3>
          <div className="entity-name">{verdict.summary}</div>
        </div>
        <span className={`badge ${levelClass} verdict-badge`}>{VERDICT_LEVEL_LABELS[verdict.level]}</span>
      </div>

      {/* Этап 1: Факты */}
      <h3 className="stage">
        1. Факты
        <Tip text="Что установлено по данным реестров: контракты, суммы, адреса, доли. Без интерпретации — только проверяемые сведения" />
      </h3>
      <div className="facts-grid">
        {verdict.facts.map((f) => (
          <div className="fact" key={f.name}>
            <div className="fact-name">{f.name}</div>
            <div className="fact-value">{f.value}</div>
          </div>
        ))}
      </div>

      {/* Этап 2: Признаки */}
      <h3 className="stage">
        2. Признаки схем
        <Tip text="Факты, совпавшие с шаблонами известных коррупционных схем. Каждое правило — отдельная схема с описанием и ссылками на законы" />
      </h3>
      {verdict.indicators.length === 0 && <p className="muted">Признаки не выявлены.</p>}
      {verdict.indicators.map((ind) => (
        <div className="indicator" key={ind.rule}>
          <span className={`badge ${ind.severity === "high" ? "high" : "medium"}`}>{SEVERITY_LABELS[ind.severity]}</span>{" "}
          <b>{ind.scheme}</b>
          <span className="mono muted"> правило {ind.rule}</span>
          <p className="muted"><Expandable text={ind.description} /></p>
          <p className="methodology-line">Методическое основание: {ind.methodology}</p>
          <LegalArticles articles={ind.articles} />
          <p className="action-line">Что запросить: {ind.action}</p>
        </div>
      ))}
      {latest?.decision === "rejected" && (
        <p className="rejected-note">
          Сигналы отклонены сотрудником {new Date(latest.created_at).toLocaleString("ru-RU")}
          {latest.comment ? ` («${latest.comment}»)` : ""}. Сигналы сохранены и остаются доступны для истории.
        </p>
      )}

      {/* Этап 3: Сигналы → правовые основания */}
      <h3 className="stage">
        3. Правовые основания
        <Tip text="Нормативные акты, которые могут быть нарушены при подтверждении схемы. Ссылки открывают основание для запросов и проверок" />
      </h3>
      {verdict.laws.length === 0 && <p className="muted">Основания отсутствуют — нарушений не выявлено.</p>}
      <div className="chips-row">
        {verdict.laws.map((law) => (
          <span className="chip" key={law}>{law}</span>
        ))}
      </div>

      {/* Рекомендация */}
      <h3 className="stage">Рекомендация</h3>
      <p>{verdict.recommendation}</p>
    </div>
  );
}
