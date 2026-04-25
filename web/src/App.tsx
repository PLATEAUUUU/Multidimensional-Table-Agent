import { useEffect } from "react";
import { LockedRoundToast } from "./components/LockedRoundToast";
import { useWebSocket } from "./hooks/useWebSocket";
import { fetchInitialSession } from "./lib/api";
import { useInterviewStore } from "./store/interview";
import type { WsEnvelope } from "./types/interview";

const SESSION_ID = "demo-session";
const WS_URL = import.meta.env.VITE_WS_URL ?? `ws://localhost:8000/ws/interview/${SESSION_ID}`;

const roundSteps = ["init", "hr", "tech", "manager", "completed"];

export default function App() {
  const {
    backendState,
    selectedStep,
    connectionState,
    reconnectAttempts,
    lockReason,
    setConnectionState,
    setReconnectAttempts,
    incrementReconnectAttempts,
    hydrateFromBackend,
    setSelectedStep
  } = useInterviewStore();

  useEffect(() => {
    fetchInitialSession(SESSION_ID)
      .then(hydrateFromBackend)
      .catch(() => {
        setConnectionState("closed");
      });
  }, [hydrateFromBackend, setConnectionState]);

  useWebSocket(WS_URL, {
    reconnectInterval: 3000,
    maxRetries: 5,
    onOpen: () => {
      setConnectionState("connected");
      setReconnectAttempts(0);
    },
    onClose: () => {
      setConnectionState("retrying");
      incrementReconnectAttempts();
    },
    onMessage: (event) => {
      const envelope = JSON.parse(event.data) as WsEnvelope;
      if (envelope.type === "session_state") {
        hydrateFromBackend(envelope.payload);
      }
    }
  });

  return (
    <main className="min-h-screen px-6 py-10 font-body text-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <header className="rounded-[2rem] border border-white/10 bg-white/5 p-8 shadow-frame backdrop-blur">
          <p className="text-sm uppercase tracking-[0.4em] text-amber-300">Interview AI Scaffold</p>
          <h1 className="mt-3 font-display text-4xl font-semibold">多 Agent 智能面试系统框架</h1>
          <p className="mt-3 max-w-3xl text-sm text-slate-300">
            当前页面只承载工程骨架，用于展示回合锁定、会话同步和 WebSocket 重连策略。
          </p>
        </header>

        <LockedRoundToast lockReason={lockReason} />

        <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-[2rem] border border-white/10 bg-slate-900/70 p-6 shadow-frame">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">流程面板</h2>
              <span className="rounded-full bg-emerald-400/15 px-3 py-1 text-xs text-emerald-200">
                websocket: {connectionState}
              </span>
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              {roundSteps.map((step) => {
                const active = backendState?.current_step === step;
                const selected = selectedStep === step;
                return (
                  <button
                    key={step}
                    type="button"
                    onClick={() => setSelectedStep(step)}
                    className={[
                      "rounded-full border px-4 py-2 text-sm transition",
                      active ? "border-amber-300 bg-amber-400/15 text-amber-100" : "border-white/10 bg-white/5",
                      selected ? "ring-2 ring-sky-400/70" : ""
                    ].join(" ")}
                  >
                    {step}
                  </button>
                );
              })}
            </div>

            <div className="mt-6 rounded-2xl bg-slate-950/70 p-4 text-sm text-slate-300">
              <div>selectedStep: {selectedStep}</div>
              <div>current_step: {backendState?.current_step ?? "unknown"}</div>
              <div>trace_id: {backendState?.trace_id ?? "pending"}</div>
            </div>
          </div>

          <aside className="rounded-[2rem] border border-white/10 bg-slate-900/70 p-6 shadow-frame">
            <h2 className="text-xl font-semibold">审计快照</h2>
            <dl className="mt-5 space-y-4 text-sm text-slate-300">
              <div>
                <dt className="text-slate-400">Agent</dt>
                <dd className="mt-1">{backendState?.active_agent ?? "supervisor"}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Decision</dt>
                <dd className="mt-1">{backendState?.route_decision?.decision ?? "bootstrap"}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Reconnect Attempts</dt>
                <dd className="mt-1">{reconnectAttempts}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Token Usage</dt>
                <dd className="mt-1">{backendState?.token_usage.total ?? 0}</dd>
              </div>
            </dl>
          </aside>
        </section>
      </div>
    </main>
  );
}
