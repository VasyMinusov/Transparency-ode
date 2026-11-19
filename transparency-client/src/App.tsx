// Каркас приложения: статус сервера → меню разделов.
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { invoke } from "@tauri-apps/api/core";
import NavSidebar, { type View } from "./components/NavSidebar";
import SearchPanel from "./components/SearchPanel";
import ReportView from "./components/ReportView";
import SignalsPanel from "./components/SignalsPanel";
import ContractsPanel from "./components/ContractsPanel";
import LawsPanel from "./components/LawsPanel";
import ModelsPanel from "./components/ModelsPanel";
import JournalPanel from "./components/JournalPanel";
import Landing from "./components/Landing";
import { primarySource } from "./data/sources";

async function checkBackend(): Promise<boolean> {
  try {
    await invoke("backend_status");
    return true;
  } catch {
    try {
      const r = await fetch("http://127.0.0.1:8000/health");
      return r.ok;
    } catch {
      return false;
    }
  }
}

function BackendGate() {
  const [starting, setStarting] = useState(false);
  const start = async () => {
    setStarting(true);
    try {
      await invoke("start_backend");
    } catch {
      alert("Запустите вручную: cd transparency-api && uv run uvicorn app.main:app --port 8000");
    }
  };
  return (
    <div className="gate">
      <div className="logo large">КП</div>
      <h1>Код прозрачности</h1>
      <p className="muted">Сервер данных недоступен по адресу 127.0.0.1:8000</p>
      <button className="btn" onClick={start} disabled={starting}>
        {starting ? "Запускаем… подождите несколько секунд" : "Запустить сервер данных"}
      </button>
    </div>
  );
}

export default function App() {
  const backend = useQuery({
    queryKey: ["backend"],
    queryFn: checkBackend,
    refetchInterval: 3000,
    retry: false,
  });
  const [view, setView] = useState<View>("check");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  // Лента сигналов + уведомления о новых сигналах высокой степени
  const signalsQuery = useQuery({
    queryKey: ["signals-nav"],
    queryFn: () => primarySource().getSignals(),
    enabled: backend.data === true,
    refetchInterval: 60000,
  });
  const signals = signalsQuery.data ?? [];
  const prevHigh = useRef(0);
  useEffect(() => {
    const high = signals.filter((s) => s.severity === "high").length;
    if (high > prevHigh.current && prevHigh.current > 0 && "Notification" in window) {
      if (Notification.permission === "granted") {
        new Notification("Код прозрачности", {
          body: `Новые сигналы высокой степени: ${high}. Требуется проверка.`,
        });
      } else if (Notification.permission !== "denied") {
        Notification.requestPermission();
      }
    }
    prevHigh.current = Math.max(prevHigh.current, high);
  }, [signals]);

  const openEntity = (id: number) => {
    setSelectedId(id);
    setView("check");
  };

  if (backend.isLoading) return <div className="gate">Проверка сервера данных…</div>;
  if (!backend.data) return <BackendGate />;

  return (
    <div className="app">
      <div className="shell">
        <NavSidebar view={view} onView={setView} signals={signals} />
        <main className="content">
          {view === "check" && (
            <div className="check-layout">
              <aside className="col-left">
                <SearchPanel onSelect={setSelectedId} />
              </aside>
              <div className="col-main">
                {selectedId !== null ? (
                  <ReportView id={selectedId} onSelect={openEntity} />
                ) : (
                  <Landing
                    signals={signals}
                    onOpenEntity={openEntity}
                    onGoSignals={() => setView("signals")}
                  />
                )}
              </div>
            </div>
          )}
          {view === "signals" && <SignalsPanel onOpenEntity={openEntity} />}
          {view === "contracts" && <ContractsPanel onOpenEntity={openEntity} />}
          {view === "laws" && <LawsPanel />}
          {view === "models" && <ModelsPanel />}
        </main>
        <aside className="col-right">
          <JournalPanel />
        </aside>
      </div>
    </div>
  );
}
