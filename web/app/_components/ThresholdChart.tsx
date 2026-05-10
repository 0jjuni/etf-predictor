"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ThresholdRow } from "@/lib/types";

export function ThresholdChart({ curve }: { curve: ThresholdRow[] }) {
  const data = [...curve]
    .sort((a, b) => a.threshold - b.threshold)
    .map((row) => ({
      threshold: row.threshold.toFixed(2),
      precision: row.precision == null ? null : +(row.precision * 100).toFixed(2),
      recall: row.recall == null ? null : +(row.recall * 100).toFixed(2),
      f1: row.f1 == null ? null : +(row.f1 * 100).toFixed(2),
    }));

  return (
    <div className="mt-4 h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="threshold"
            tick={{ fontSize: 11, fill: "#64748b" }}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#64748b" }}
            tickFormatter={(v: number) => `${v}%`}
          />
          <Tooltip
            contentStyle={{
              borderRadius: 8,
              border: "1px solid #e2e8f0",
              fontSize: 12,
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="precision"
            name="정밀도"
            stroke="#4f46e5"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="recall"
            name="재현율"
            stroke="#10b981"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="f1"
            name="F1"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
