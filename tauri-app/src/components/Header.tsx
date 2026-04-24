import { Activity, Circle, Settings } from "lucide-react";

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
      data-tauri-drag-region
    >
      <div
        className="ml-16 flex items-center gap-2"
        data-tauri-drag-region
      >
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
          ollama:{" "}
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
