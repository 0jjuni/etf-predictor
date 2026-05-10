import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronRight } from "lucide-react";
import {
  fetchProbabilityForSymbol,
  fetchUniverseLatest,
} from "@/lib/queries";
import { formatKoreanDate, pct } from "@/lib/format";
import { supabase } from "@/lib/supabase";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatTile } from "@/components/ui/stat-tile";

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
  if (!row) return { title: `${symbol}` };
  return {
    title: `${row.name} (${row.symbol})`,
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
  if (!row) notFound();

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
      <nav className="flex items-center gap-1 text-xs text-slate-500">
        <Link href="/" className="hover:text-indigo-600">
          홈
        </Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-700">{row.symbol}</span>
      </nav>

      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="font-mono text-xs text-slate-400">{row.symbol}</div>
              <h1 className="mt-1 text-2xl font-bold tracking-tight">
                {row.name}
              </h1>
              <div className="mt-1 text-xs text-slate-500">
                기준일 {formatKoreanDate(row.target_date)}
              </div>
            </div>
            {recommended ? (
              <Badge variant="success">추천 종목</Badge>
            ) : (
              <Badge variant="secondary">기준 미달</Badge>
            )}
          </div>

          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
            <StatTile
              label="상승 확률"
              value={pct(row.probability, 1)}
              tone={recommended ? "positive" : "default"}
            />
            <StatTile label="기준 임계값" value="70.0%" tone="muted" />
            <StatTile
              label="모델 평가"
              value={recommended ? "통과" : "미달"}
              tone={recommended ? "positive" : "muted"}
              className="hidden sm:block"
            />
          </div>
        </CardContent>
      </Card>

      <section>
        <h2 className="mb-3 text-base font-bold tracking-tight">최근 추천 이력</h2>
        {hist.length === 0 ? (
          <Card>
            <CardContent className="py-10 text-center">
              <p className="text-sm text-slate-500">
                이 종목이 70% 이상으로 추천된 이력이 아직 없습니다.
              </p>
            </CardContent>
          </Card>
        ) : (
          <Card className="overflow-hidden">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-[11px] uppercase text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold">날짜</th>
                  <th className="px-4 py-3 text-right font-semibold">예측 확률</th>
                  <th className="px-4 py-3 text-right font-semibold">실제 변동</th>
                  <th className="px-4 py-3 text-right font-semibold">결과</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {hist.map((r) => (
                  <tr key={r.target_date}>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600 dark:text-slate-400">
                      {r.target_date}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      {pct(r.probability, 1)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      {r.actual_change == null
                        ? "—"
                        : `${(r.actual_change * 100).toFixed(2)}%`}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {r.outcome == null ? (
                        <span className="text-slate-400">—</span>
                      ) : r.outcome ? (
                        <Badge variant="success">적중</Badge>
                      ) : (
                        <Badge variant="danger">실패</Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </section>

      <Card className="border-amber-200 bg-amber-50 dark:border-amber-500/30 dark:bg-amber-500/10">
        <CardContent className="p-4 text-xs text-amber-900 dark:text-amber-200">
          본 페이지는 정보 제공 목적이며, 투자 권유가 아닙니다. 모델은 과거
          가격·모멘텀 패턴만 학습한 결과로 시장 급변에 약합니다.
        </CardContent>
      </Card>
    </div>
  );
}
