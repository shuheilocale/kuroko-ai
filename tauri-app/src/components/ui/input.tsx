import * as React from "react";

import { cn } from "@/lib/utils";

const inputCls = [
  "h-8 w-full rounded-md border px-2.5 text-[13px]",
  "border-[color:var(--color-border)] bg-[color:var(--color-bg)]",
  "text-[color:var(--color-fg)] placeholder:text-[color:var(--color-fg-subtle)]",
  "transition-colors",
  "hover:border-[color:var(--color-border-strong)]",
  "focus:border-[color:var(--color-accent)] focus:outline-none",
  "disabled:cursor-not-allowed disabled:opacity-50",
].join(" ");

export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => (
  <input ref={ref} className={cn(inputCls, className)} {...props} />
));
Input.displayName = "Input";
