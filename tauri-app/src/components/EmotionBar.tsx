import { cn } from "@/lib/utils";

interface Props {
  label: string;
  value: number;
  color: string;
  active?: boolean;
}

export function EmotionBar({ label, value, color, active }: Props) {
  const pct = Math.min(100, Math.max(0, value * 100));
  return (
    <div className="flex items-center gap-2">
      <span
        className={cn(
          "w-4 shrink-0 text-center text-[11px] font-medium",
          active
            ? "text-[color:var(--color-fg)]"
            : "text-[color:var(--color-fg-muted)]",
        )}
        style={active ? { color } : undefined}
      >
        {label}
      </span>
      <div className="h-1 flex-1 overflow-hidden rounded-full bg-[color:var(--color-surface-2)]">
        <div
          className="h-full transition-[width] duration-100 ease-out"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="w-8 text-right font-mono text-[10px] tabular-nums text-[color:var(--color-fg-muted)]">
        {value.toFixed(2)}
      </span>
    </div>
  );
}
