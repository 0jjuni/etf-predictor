import * as React from "react";
import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "secondary" | "success" | "warning" | "danger" | "outline";

const variants: Record<BadgeVariant, string> = {
  default:
    "bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300",
  secondary:
    "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  success:
    "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300",
  warning:
    "bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-200",
  danger:
    "bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300",
  outline:
    "border border-slate-200 text-slate-600 bg-transparent dark:border-slate-700 dark:text-slate-300",
};

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
