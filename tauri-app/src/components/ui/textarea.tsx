import * as React from "react";

import { cn } from "@/lib/utils";

const cls = [
  "min-h-[64px] w-full rounded-md border px-2.5 py-1.5 text-[13px]",
  "border-[color:var(--color-border)] bg-[color:var(--color-bg)]",
  "text-[color:var(--color-fg)] placeholder:text-[color:var(--color-fg-subtle)]",
  "transition-colors resize-y leading-relaxed",
  "hover:border-[color:var(--color-border-strong)]",
  "focus:border-[color:var(--color-accent)] focus:outline-none",
  "disabled:cursor-not-allowed disabled:opacity-50",
].join(" ");

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea ref={ref} className={cn(cls, className)} {...props} />
));
Textarea.displayName = "Textarea";
