import Link from "next/link";
import { notFound } from "next/navigation";
import {
  fetchProbabilityForSymbol,
  fetchUniverseLatest,
} from "@/lib/queries";
import { formatKoreanDate, pct } from "@/lib/format";
import { supabase } from "@/lib/supabase";

// Statically pre-render every ETF in the latest universe (revalidate daily).
export const revalidate = 600;
export const dynamicParams = true;

export async function generateStaticParams() {
  const { rows } = await fetchUniverseLatest();
  return rows.slice(0, 200).map((r) => ({ symbol: r.symbol }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol } = await params;
  const row = await fetchProbabilityForSymbol(symbol);
  if (!row) return { title: `${symbol} · ETF 종가 예측` };
  return {
    title: `${row.name} (${row.symbol}) · ETF 종가 예측`,
    description: `${row.name} 코드 ${row.symbol} — 모델 추정 다음 거래일 +2.5% 상승 확률 ${(row.probability * 100).toFixed(1)}% (기준 ${row.target_date})`,
  };
}

export default async function EtfPage({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol } = await params;
  const row = await fetchProbabilityForSymbol(symbol);
  if (!row) {
    notFound();
  }

  // Recent prediction history for this symbol from the predictions table.
  const histRes = await supabase
    .from("predictions")
    .select("target_date,probability,outcome,actual_change")
    .eq("symbol", symbol)
    .order("target_date", { ascending: false })
    .limit(60);
  const hist = histRes.data ?? [];
  const recommended = row.probability >= 0.7;

  return (
    <div className="space-y-6">
      <nav className="text-xs text-slate-500">
        <Link className="hover:underline" href="/">
          홈
        </Link>{" "}
        / 종목
      </nav>

      <header className="rounded-2xl border border-slate-200 bg-white p-6">
        <div className="font-mono text-xs text-slate-500">{row.symbol}</div>
        <h1 className="mt-1 text-2xl font-bold">{row.name}</h1>
        <div className="mt-1 text-xs text-slate-500">
          기준일 {formatKoreanDate(row.target_date)}
        </div>
        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Stat label="상승 확률" value={pct(row.probability, 1)} highlight />
          <Stat
            label="추천 여부"
            value={recommended ? "추천 종목" : "기준 미달"}
            tone={recommended ? "positive" : "neutral"}
          />
          <Stat label="기준 임계값" value="70.0%" tone="neutral" />
        </div>
      </header>

      <section className="rounded-2xl border border-slate-200 bg-white p-5">
        <h2 className="text-base font-semibold">최근 추천 이력</h2>
        {hist.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">
            이 종목이 70% 이상으로 추천된 이력이 아직 없습니다.
          </p>
        ) : (
          <div className="mt-3 overflow-hidden rounded-lg border border-slate-200">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2 text-left">날짜</th>
                  <th className="px-3 py-2 text-right">예측 확률</th>
                  <th className="px-3 py-2 text-right">실제 변동</th>
                  <th className="px-3 py-2 text-right">결과</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {hist.map((r) => (
                  <tr key={r.target_date}>
                    <td className="px-3 py-2 font-mono text-xs">
                      {r.target_date}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {pct(r.probability, 1)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {r.actual_change == null
                        ? "—"
                        : `${(r.actual_change * 100).toFixed(2)}%`}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {r.outcome == null
                        ? "—"
                        : r.outcome
                          ? "✓ 적중"
                          : "✗ 실패"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900">
        본 페이지는 정보 제공 목적이며, 투자 권유가 아닙니다. 모델은 과거
        가격·모멘텀 패턴만 학습한 결과로 시장 급변에 약합니다.
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  highlight,
  tone,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  tone?: "positive" | "neutral";
}) {
  const valueColor = highlight
    ? "text-indigo-600"
    : tone === "positive"
      ? "text-emerald-600"
      : "text-slate-800";
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className={`mt-1 text-xl font-bold ${valueColor}`}>{value}</div>
    </div>
  );
}
