"use client";

import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Prediction } from "@/lib/types";

interface Point {
  date: string;
  equity: number;
}

function buildEquityCurve(history: Prediction[]): Point[] {
  if (history.length === 0) return [];
  const byDate = new Map<string, number[]>();
  for (const row of history) {
    if (row.actual_change == null) continue;
    const arr = byDate.get(row.target_date) ?? [];
    arr.push(row.actual_change);
    byDate.set(row.target_date, arr);
  }
  const dates = [...byDate.keys()].sort();
  let equity = 100;
  return dates.map((d) => {
    const changes = byDate.get(d) ?? [];
    const dailyReturn =
      changes.reduce((s, x) => s + x, 0) / Math.max(changes.length, 1);
    equity = equity * (1 + dailyReturn);
    return { date: d, equity: +equity.toFixed(3) };
  });
}

export function EquityCurve({ history }: { history: Prediction[] }) {
  const data = useMemo(() => buildEquityCurve(history), [history]);
  if (data.length === 0) return null;

  const final = data[data.length - 1].equity;
  const totalReturnPct = final - 100;
  const dailyReturns = data.map((p, i) =>
    i === 0 ? 0 : p.equity / data[i - 1].equity - 1,
  );
  const avgReturn =
    dailyReturns.length > 0
      ? dailyReturns.reduce((s, x) => s + x, 0) / dailyReturns.length
      : 0;

  return (
    <div className="mt-4 space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <Stat
          label="누적 수익률"
          value={`${totalReturnPct >= 0 ? "+" : ""}${totalReturnPct.toFixed(2)}%`}
          tone={totalReturnPct >= 0 ? "positive" : "negative"}
        />
        <Stat label="거래일 수" value={`${data.length}일`} />
        <Stat
          label="평균 일일 수익"
          value={`${avgReturn >= 0 ? "+" : ""}${(avgReturn * 100).toFixed(2)}%`}
          tone={avgReturn >= 0 ? "positive" : "negative"}
        />
      </div>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: "#64748b" }}
              tickFormatter={(v) => v.slice(5)}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#64748b" }}
              domain={["dataMin - 1", "dataMax + 1"]}
            />
            <Tooltip
              contentStyle={{
                borderRadius: 8,
                border: "1px solid #e2e8f0",
                fontSize: 12,
              }}
              formatter={(v) => [
                typeof v === "number" ? v.toFixed(2) : String(v),
                "자산 가치",
              ]}
              labelStyle={{ color: "#475569" }}
            />
            <Line
              type="monotone"
              dataKey="equity"
              stroke="#4f46e5"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "positive" | "negative";
}) {
  const color =
    tone === "positive"
      ? "text-emerald-600"
      : tone === "negative"
        ? "text-rose-600"
        : "text-slate-800";
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className={`mt-1 text-lg font-bold ${color}`}>{value}</div>
    </div>
  );
}
