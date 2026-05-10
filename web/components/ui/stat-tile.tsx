import { cn } from "@/lib/utils";

type Tone = "default" | "positive" | "negative" | "muted";

const toneClass: Record<Tone, string> = {
  default: "text-slate-900 dark:text-slate-100",
  positive: "text-emerald-600 dark:text-emerald-400",
  negative: "text-rose-600 dark:text-rose-400",
  muted: "text-slate-500 dark:text-slate-400",
};

interface StatTileProps {
  label: string;
  value: string;
  hint?: string;
  tone?: Tone;
  className?: string;
}

export function StatTile({
  label,
  value,
  hint,
  tone = "default",
  className,
}: StatTileProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm dark:border-slate-800 dark:bg-slate-900",
        className,
      )}
    >
      <div className="text-[10.5px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
        {label}
      </div>
      <div
        className={cn(
          "mt-1.5 text-xl font-bold tabular-nums tracking-tight",
          toneClass[tone],
        )}
      >
        {value}
      </div>
      {hint && (
        <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
          {hint}
        </div>
      )}
    </div>
  );
}
