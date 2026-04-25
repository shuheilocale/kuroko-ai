import { Activity, Circle, Hourglass, Settings } from "lucide-react";

import { AudioMeter } from "@/components/AudioMeter";
import { TurnTakingGauge } from "@/components/TurnTakingGauge";
import { Button } from "@/components/ui/button";
import type { StateSocketStatus } from "@/lib/api";
import type { PipelineState } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  state: PipelineState | null;
  status: StateSocketStatus;
  onOpenSettings: () => void;
}

export function Header({ state, status, onOpenSettings }: Props) {
  const statusColor =
    status === "open"
      ? "text-[color:var(--color-success)]"
      : status === "error"
        ? "text-[color:var(--color-danger)]"
        : "text-[color:var(--color-fg-muted)]";

  return (
    <header
      className={cn(
        "flex h-11 items-center gap-4 border-b px-4",
        "border-[color:var(--color-border)] bg-[color:var(--color-surface)]",
      )}
    >
      <div className="flex items-center gap-2">
        <Activity
          className="size-4 text-[color:var(--color-accent)]"
          aria-hidden
        />
        <h1 className="font-medium tracking-tight">ささやき女将</h1>
      </div>

      <div className="flex items-center gap-5">
        <AudioMeter
          label="mic"
          value={state?.mic_level ?? 0}
          color="var(--color-mic)"
        />
        <AudioMeter
          label="sys"
          value={state?.system_level ?? 0}
          color="var(--color-system)"
        />
        <TurnTakingGauge turn={state?.turn_taking} />
        <SilenceIndicator
          seconds={state?.silence_seconds ?? 0}
          threshold={state?.silence_rescue_seconds ?? 6}
          enabled={state?.silence_rescue_enabled ?? false}
        />
      </div>

      <div className="ml-auto flex items-center gap-3">
        <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider">
          <Circle
            className={cn("size-2 fill-current", statusColor)}
            strokeWidth={0}
          />
          <span className={statusColor}>{status}</span>
        </div>
        <span className="font-mono text-[10px] text-[color:var(--color-fg-subtle)]">
          {state?.llm_backend === "llamacpp" ? "llama.cpp" : "ollama"}
          :{" "}
          <span
            className={
              state?.ollama_ok
                ? "text-[color:var(--color-success)]"
                : "text-[color:var(--color-danger)]"
            }
          >
            {state?.ollama_ok ? "ok" : "down"}
          </span>
        </span>
        <Button
          variant="ghost"
          size="icon"
          onClick={onOpenSettings}
          aria-label="設定を開く"
        >
          <Settings className="size-4" />
        </Button>
      </div>
    </header>
  );
}

function SilenceIndicator({
  seconds,
  threshold,
  enabled,
}: {
  seconds: number;
  threshold: number;
  enabled: boolean;
}) {
  if (!enabled || seconds < 1.5) return null;
  const hot = seconds >= threshold;
  return (
    <span
      className={cn(
        "flex items-center gap-1 font-mono text-[10px] tabular-nums",
        "uppercase tracking-wider",
        hot
          ? "text-[color:var(--color-accent)]"
          : "text-[color:var(--color-fg-muted)]",
      )}
      title="沈黙が続くとレスキューが発火します"
    >
      <Hourglass className="size-3" />
      {seconds.toFixed(1)}s
    </span>
  );
}
