import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap",
    "rounded-md text-xs font-medium transition-colors",
    "focus-visible:outline-none",
    "disabled:pointer-events-none disabled:opacity-50",
  ].join(" "),
  {
    variants: {
      variant: {
        default:
          "bg-[color:var(--color-accent)] text-white hover:bg-[color:var(--color-accent-hover)]",
        secondary:
          "bg-[color:var(--color-surface-2)] text-[color:var(--color-fg)] hover:bg-[color:var(--color-border)]",
        ghost:
          "text-[color:var(--color-fg-muted)] hover:bg-[color:var(--color-surface-2)] hover:text-[color:var(--color-fg)]",
        outline:
          "border border-[color:var(--color-border)] bg-transparent text-[color:var(--color-fg)] hover:bg-[color:var(--color-surface-2)] hover:border-[color:var(--color-border-strong)]",
      },
      size: {
        default: "h-8 px-3",
        sm: "h-7 px-2.5",
        icon: "h-8 w-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  ),
);
Button.displayName = "Button";

export { buttonVariants };
