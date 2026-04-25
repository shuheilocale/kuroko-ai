import { cn } from "@/lib/utils";

interface Props {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  label?: string;
}

export function Switch({ checked, onChange, disabled, label }: Props) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-5 w-9 shrink-0 rounded-full",
        "border transition-colors",
        "disabled:cursor-not-allowed disabled:opacity-50",
        checked
          ? "border-[color:var(--color-accent)] bg-[color:var(--color-accent)]"
          : "border-[color:var(--color-border)] bg-[color:var(--color-surface-2)]",
      )}
    >
      <span
        className={cn(
          "absolute top-1/2 size-3.5 -translate-y-1/2 rounded-full bg-white",
          "shadow-sm transition-transform duration-150 ease-out",
          checked ? "translate-x-[18px]" : "translate-x-[2px]",
        )}
      />
    </button>
  );
}
