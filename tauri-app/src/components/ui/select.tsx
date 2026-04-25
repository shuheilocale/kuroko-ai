import { ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";

interface Option {
  value: string;
  label?: string;
}

interface Props {
  value: string;
  options: (string | Option)[];
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}

export function Select({
  value,
  options,
  onChange,
  placeholder,
  className,
  disabled,
}: Props) {
  const normalized: Option[] = options.map((o) =>
    typeof o === "string" ? { value: o, label: o } : o,
  );

  return (
    <div className={cn("relative", className)}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={cn(
          "h-8 w-full appearance-none rounded-md border pr-8 pl-2.5",
          "text-[13px] border-[color:var(--color-border)]",
          "bg-[color:var(--color-bg)] text-[color:var(--color-fg)]",
          "transition-colors",
          "hover:border-[color:var(--color-border-strong)]",
          "focus:border-[color:var(--color-accent)] focus:outline-none",
          "disabled:cursor-not-allowed disabled:opacity-50",
        )}
      >
        {placeholder && value === "" && (
          <option value="" disabled hidden>
            {placeholder}
          </option>
        )}
        {normalized.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label ?? o.value}
          </option>
        ))}
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-2 top-1/2 size-3.5 -translate-y-1/2 text-[color:var(--color-fg-muted)]"
        strokeWidth={2}
      />
    </div>
  );
}
