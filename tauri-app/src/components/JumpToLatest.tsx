import { ArrowDown } from "lucide-react";

import { cn } from "@/lib/utils";

interface Props {
  onClick: () => void;
  label?: string;
}

export function JumpToLatest({ onClick, label = "最新へ" }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "absolute bottom-3 left-1/2 flex -translate-x-1/2 items-center gap-1.5",
        "rounded-full border px-2.5 py-1 text-[11px] font-medium",
        "border-[color:var(--color-accent)]",
        "bg-[color:var(--color-accent)] text-white",
        "shadow-lg hover:bg-[color:var(--color-accent-hover)]",
        "transition-colors",
      )}
    >
      <ArrowDown className="size-3" />
      {label}
    </button>
  );
}
