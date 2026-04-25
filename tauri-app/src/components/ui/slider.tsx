import { cn } from "@/lib/utils";

interface Props {
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (v: number) => void;
  disabled?: boolean;
  className?: string;
}

export function Slider({
  value,
  min,
  max,
  step = 0.01,
  onChange,
  disabled,
  className,
}: Props) {
  return (
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(Number(e.target.value))}
      className={cn(
        "h-1 w-full cursor-pointer appearance-none rounded-full",
        "bg-[color:var(--color-surface-2)]",
        "disabled:cursor-not-allowed disabled:opacity-50",
        // WebKit thumb
        "[&::-webkit-slider-thumb]:appearance-none",
        "[&::-webkit-slider-thumb]:size-3.5",
        "[&::-webkit-slider-thumb]:rounded-full",
        "[&::-webkit-slider-thumb]:bg-[color:var(--color-accent)]",
        "[&::-webkit-slider-thumb]:border",
        "[&::-webkit-slider-thumb]:border-[color:var(--color-accent)]",
        "[&::-webkit-slider-thumb]:transition-transform",
        "[&::-webkit-slider-thumb]:hover:scale-110",
        // Firefox thumb
        "[&::-moz-range-thumb]:size-3.5",
        "[&::-moz-range-thumb]:rounded-full",
        "[&::-moz-range-thumb]:border-0",
        "[&::-moz-range-thumb]:bg-[color:var(--color-accent)]",
        className,
      )}
    />
  );
}
