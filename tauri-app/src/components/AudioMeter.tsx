import { cn } from "@/lib/utils";

interface Props {
  label: string;
  value: number;
  color: string;
  width?: number;
}

export function AudioMeter({ label, value, color, width = 80 }: Props) {
  const pct = Math.min(100, Math.max(0, value * 100));
  return (
    <div className="flex items-center gap-2">
      <span
        className={cn(
          "font-mono text-[10px] uppercase tracking-wider",
          "text-[color:var(--color-fg-muted)]",
        )}
      >
        {label}
      </span>
      <div
        className="h-1 overflow-hidden rounded-full bg-[color:var(--color-surface-2)]"
        style={{ width }}
      >
        <div
          className="h-full transition-[width] duration-75 ease-out"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}
