import type { TurnTakingState } from "@/lib/types";

interface Props {
  turn: TurnTakingState | undefined;
  threshold?: number;
}

export function TurnTakingGauge({ turn, threshold = 0.6 }: Props) {
  if (!turn || !turn.enabled) {
    return (
      <div className="flex items-center gap-2">
        <span className="font-mono text-[10px] uppercase tracking-wider text-[color:var(--color-fg-subtle)]">
          turn
        </span>
        <span className="text-[10px] text-[color:var(--color-fg-subtle)]">
          off
        </span>
      </div>
    );
  }

  const hot = turn.p_now >= threshold;

  return (
    <div className="flex items-center gap-2">
      <span className="font-mono text-[10px] uppercase tracking-wider text-[color:var(--color-fg-muted)]">
        turn
      </span>
      <div className="relative h-1.5 w-28 overflow-hidden rounded-full bg-[color:var(--color-surface-2)]">
        <div
          className="absolute inset-y-0 left-0 bg-[color:var(--color-accent-soft)] transition-[width] duration-100 ease-out"
          style={{ width: `${turn.p_future * 100}%` }}
        />
        <div
          className="absolute inset-y-0 left-0 transition-[width,background-color] duration-100 ease-out"
          style={{
            width: `${turn.p_now * 100}%`,
            backgroundColor: hot
              ? "var(--color-accent)"
              : "var(--color-fg-muted)",
          }}
        />
      </div>
      <span className="w-9 font-mono text-[10px] tabular-nums text-[color:var(--color-fg-muted)]">
        {turn.p_now.toFixed(2)}
      </span>
    </div>
  );
}
