import { useEffect } from "react";
import { Activity, Circle, Mic, Speaker } from "lucide-react";

import { connectStateSocket } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";

export default function App() {
  const state = useAppStore((s) => s.state);
  const status = useAppStore((s) => s.status);
  const setState = useAppStore((s) => s.setState);
  const setStatus = useAppStore((s) => s.setStatus);

  useEffect(() => {
    return connectStateSocket({
      onState: setState,
      onStatus: setStatus,
    });
  }, [setState, setStatus]);

  const statusColor =
    status === "open"
      ? "text-[color:var(--color-success)]"
      : status === "error"
        ? "text-[color:var(--color-danger)]"
        : "text-[color:var(--color-fg-muted)]";

  return (
    <main className="flex h-full flex-col">
      <header
        className={cn(
          "flex items-center gap-3 border-b px-4 py-2",
          "border-[color:var(--color-border)]",
          "bg-[color:var(--color-surface)]",
        )}
      >
        <Activity className="size-4 text-[color:var(--color-accent)]" />
        <h1 className="font-medium tracking-tight">ささやき女将</h1>
        <span className="text-[color:var(--color-fg-subtle)]">·</span>
        <span className="text-[color:var(--color-fg-muted)] text-xs">
          AI Meeting Assistant
        </span>
        <div className="ml-auto flex items-center gap-2 font-mono text-xs">
          <Circle
            className={cn("size-2 fill-current", statusColor)}
            strokeWidth={0}
          />
          <span className={statusColor}>{status}</span>
        </div>
      </header>

      <section className="flex-1 overflow-auto p-6">
        {state === null ? (
          <div className="text-[color:var(--color-fg-muted)]">
            Python バックエンドからの状態受信を待機中…
          </div>
        ) : (
          <div className="space-y-4">
            <DebugStat
              icon={<Mic className="size-4" />}
              label="Mic"
              value={state.mic_device || "(未設定)"}
              level={state.mic_level}
            />
            <DebugStat
              icon={<Speaker className="size-4" />}
              label="System"
              value={state.system_device || "(未設定)"}
              level={state.system_level}
            />
            <div className="text-xs text-[color:var(--color-fg-muted)]">
              transcripts: {state.transcripts.length} · entities:{" "}
              {state.entities.length} · ollama:{" "}
              {state.ollama_ok ? "ok" : "down"} · p_now:{" "}
              {state.turn_taking.p_now.toFixed(2)}
            </div>
            {state.error && (
              <div className="rounded-md border border-[color:var(--color-danger)]/40 bg-[color:var(--color-danger)]/10 p-3 text-[color:var(--color-danger)]">
                {state.error}
              </div>
            )}
          </div>
        )}
      </section>
    </main>
  );
}

function DebugStat({
  icon,
  label,
  value,
  level,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  level: number;
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2 text-[color:var(--color-fg-muted)]">
        {icon}
        <span className="text-xs uppercase tracking-wider">{label}</span>
      </div>
      <div className="font-mono text-sm">{value}</div>
      <div className="ml-auto h-1 w-32 overflow-hidden rounded-full bg-[color:var(--color-surface-2)]">
        <div
          className="h-full bg-[color:var(--color-accent)] transition-[width] duration-100 ease-out"
          style={{ width: `${Math.min(100, level * 100)}%` }}
        />
      </div>
      <div className="w-12 text-right font-mono text-xs text-[color:var(--color-fg-muted)]">
        {level.toFixed(2)}
      </div>
    </div>
  );
}
