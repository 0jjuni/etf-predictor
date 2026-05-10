import { cn } from "@/lib/utils";

type Tone = "default" | "positive" | "negative" | "muted";

const toneClass: Record<Tone, string> = {
  default: "text-slate-900",
  positive: "text-emerald-600",
  negative: "text-rose-600",
  muted: "text-slate-500",
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
        "rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm",
        className,
      )}
    >
      <div className="text-[10.5px] font-medium uppercase tracking-wider text-slate-500">
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
        <div className="mt-0.5 text-xs text-slate-500">{hint}</div>
      )}
    </div>
  );
}
