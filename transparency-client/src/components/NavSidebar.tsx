// Боковое меню разделов. Значок у «Сигналов» — число сигналов высокой степени.
import { getSources } from "../data/sources";
import { SOURCE_LABELS } from "../data/types";
import type { Signal } from "../data/types";

export type View = "check" | "signals" | "contracts" | "network" | "laws" | "models";

const MENU: { key: View; label: string; tip: string }[] = [
  { key: "check", label: "Проверка сущностей", tip: "Поиск организации и аналитический отчёт с экспертным вердиктом" },
  { key: "signals", label: "Сигналы", tip: "Лента выявленных признаков коррупционных схем по всем сущностям" },
  { key: "contracts", label: "Контракты", tip: "Реестр контрактов. По мере подключения реестров проверка проводится по каждому контракту" },
  { key: "laws", label: "Нормативная база", tip: "Нормативно-правовые акты, на которые ссылается экспертная система" },
  { key: "models", label: "Модели", tip: "Управление локальными моделями (Ollama) и выбор способа озвучивания агента" },
  { key: "network", label: "Сеть", tip: "Интерактивный граф всех сущностей и связей с оценками риска" },
];

export default function NavSidebar({
  view, onView, signals,
}: { view: View; onView: (v: View) => void; signals: Signal[] }) {
  const highCount = signals.filter((s) => s.severity === "high").length;
  return (
    <nav className="nav">
      {MENU.map((item) => (
        <button
          key={item.key}
          className={`nav-item ${view === item.key ? "active" : ""}`}
          onClick={() => onView(item.key)}
        >
          <span data-tip={item.tip}>{item.label}</span>
          {item.key === "signals" && highCount > 0 && (
            <span className="nav-badge" data-tip="Сигналов высокой степени, требующих проверки">
              {highCount}
            </span>
          )}
        </button>
      ))}
      <div className="nav-sources">
        <div className="muted small" data-tip="Источники, подключённые через единый слой данных">Источники данных</div>
        {getSources().map((s) => (
          <span className="chip" key={s.id}>{SOURCE_LABELS[s.id] ?? s.title}</span>
        ))}
      </div>
    </nav>
  );
}
