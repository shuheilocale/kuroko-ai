import type { StyleKey } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  style: StyleKey;
  active?: boolean;
  disabled?: boolean;
  onClick: (s: StyleKey) => void;
}

export function StyleButton({ style, active, disabled, onClick }: Props) {
  return (
    <button
      type="button"
      onClick={() => onClick(style)}
      disabled={disabled}
      aria-pressed={active}
      className={cn(
        "h-8 rounded-md border px-2.5 text-xs font-medium transition-colors",
        "disabled:cursor-wait disabled:opacity-60",
        active
          ? [
              "border-[color:var(--color-accent)]",
              "bg-[color:var(--color-accent-soft)]",
              "text-[color:var(--color-fg)]",
            ].join(" ")
          : [
              "border-[color:var(--color-border)]",
              "bg-[color:var(--color-surface)]",
              "text-[color:var(--color-fg-muted)]",
              "hover:border-[color:var(--color-border-strong)]",
              "hover:bg-[color:var(--color-surface-2)]",
              "hover:text-[color:var(--color-fg)]",
            ].join(" "),
      )}
    >
      {style}
    </button>
  );
}
