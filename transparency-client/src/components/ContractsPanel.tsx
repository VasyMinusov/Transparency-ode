// Реестр контрактов: по мере подключения реестров каждый контракт проходит проверку.
// Проверка трёхуровневая: «в норме» / «средняя степень» / «высокая степень» —
// по максимальной степени серьёзности сигналов сторон контракта.
import { useQuery } from "@tanstack/react-query";
import { primarySource } from "../data/sources";
import { SOURCE_LABELS } from "../data/types";

function formatMoney(v: number): string {
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)} млн ₽`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(0)} тыс. ₽`;
  return `${v.toFixed(0)} ₽`;
}

const CHECK: Record<string, { label: string; cls: string; tip: string }> = {
  high: { label: "Высокая степень", cls: "high",
    tip: "У одной из сторон есть сигнал высокой степени — проверка обязательна" },
  medium: { label: "Средняя степень", cls: "medium",
    tip: "У одной из сторон есть сигнал средней степени — рекомендуется выборочная проверка" },
  none: { label: "В норме", cls: "low",
    tip: "Сигналов у сторон контракта не выявлено" },
};

export default function ContractsPanel({ onOpenEntity }: { onOpenEntity: (id: number) => void }) {
  const { data: contracts, isLoading } = useQuery({
    queryKey: ["contracts"],
    queryFn: () => primarySource().getContracts(),
  });

  if (isLoading) return <div className="card skeleton">Загружаем реестр контрактов…</div>;

  const counts = { high: 0, medium: 0, none: 0 };
  contracts?.forEach((c) => counts[c.severity]++);

  return (
    <div className="card">
      <h3>Реестр контрактов</h3>
      <p className="muted">
        Контракты из подключённых источников. Проверка трёхуровневая: по максимальной
        степени сигналов сторон.
        {contracts && <> Высокая: {counts.high} · средняя: {counts.medium} · в норме: {counts.none}.</>}
      </p>
      <table className="table">
        <thead>
          <tr>
            <th>Номер</th><th>Дата</th><th>Заказчик</th><th>Поставщик</th>
            <th>Предмет</th><th className="num">Сумма</th><th>Источник</th><th>Проверка</th>
          </tr>
        </thead>
        <tbody>
          {contracts?.map((c) => (
            <tr key={c.contract_number}>
              <td className="mono">{c.contract_number}</td>
              <td className="mono">{c.date}</td>
              <td><button className="link" onClick={() => onOpenEntity(c.customer.id)}>{c.customer.name}</button></td>
              <td><button className="link" onClick={() => onOpenEntity(c.supplier.id)}>{c.supplier.name}</button></td>
              <td>{c.subject}</td>
              <td className="num">{formatMoney(c.amount)}</td>
              <td><span className="chip">{SOURCE_LABELS[c.source] ?? c.source}</span></td>
              <td>
                <span className={`badge ${CHECK[c.severity].cls}`} data-tip={CHECK[c.severity].tip}>
                  {CHECK[c.severity].label}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
