import Link from "next/link";
import { ArrowUpRight, ChartLine } from "lucide-react";
import {
  fetchLatestModelMetrics,
  fetchLatestPicks,
  fetchResolvedHistory,
} from "@/lib/queries";
import { formatKoreanDate, pct } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EquityCurve } from "./_components/EquityCurve";

export const revalidate = 300;

export default async function HomePage() {
  const [{ targetDate, picks }, metrics, history] = await Promise.all([
    fetchLatestPicks(),
    fetchLatestModelMetrics(),
    fetchResolvedHistory(500),
  ]);

  const fallbackPicks = metrics?.fallback_picks_json ?? [];
  const hasPicks = picks.length > 0;
  const showFallback = !hasPicks && fallbackPicks.length > 0;

  // Quick stats for the hero strip.
  const totalResolved = history.length;
  const totalHits = history.filter((h) => h.outcome === true).length;
  const empiricalPrecision =
    totalResolved > 0 ? totalHits / totalResolved : null;

  return (
    <div className="space-y-10">
      <Hero
        targetDate={targetDate}
        recommendedCount={hasPicks ? picks.length : 0}
        empiricalPrecision={empiricalPrecision}
        totalResolved={totalResolved}
      />

      <section className="space-y-4">
        <header className="flex items-baseline justify-between">
          <div>
            <h2 className="text-lg font-bold tracking-tight">오늘의 추천</h2>
            <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">
              상승확률 70% 이상으로 모델이 골라낸 종목입니다.
            </p>
          </div>
          {targetDate && (
            <Badge variant="secondary">{formatKoreanDate(targetDate)}</Badge>
          )}
        </header>

        {hasPicks ? (
          <PicksGrid picks={picks} />
        ) : showFallback ? (
          <FallbackBlock items={fallbackPicks} date={targetDate} />
        ) : (
          <EmptyPicks date={targetDate} />
        )}
      </section>

      {history.length > 0 && (
        <section>
          <header className="mb-4">
            <h2 className="text-lg font-bold tracking-tight">추천대로 샀다면?</h2>
            <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">
              매일 추천 종목을 동일 비중으로 매수해 다음 거래일 종가에 매도했다고
              가정한 누적 자산 가치 곡선입니다.
            </p>
          </header>
          <Card>
            <CardContent className="pt-5">
              <EquityCurve history={history} />
            </CardContent>
          </Card>
        </section>
      )}

    </div>
  );
}

function Hero({
  targetDate,
  recommendedCount,
  empiricalPrecision,
  totalResolved,
}: {
  targetDate: string | null;
  recommendedCount: number;
  empiricalPrecision: number | null;
  totalResolved: number;
}) {
  return (
    <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-600 via-indigo-700 to-violet-700 px-6 py-9 text-white shadow-xl shadow-indigo-500/20 sm:px-10 sm:py-12">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(255,255,255,0.18),_transparent_60%)]" />
      <div className="relative">
        <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-indigo-100">
          Korean ETF · Daily Signal
        </div>
        <h1 className="mt-3 max-w-2xl text-2xl font-bold leading-tight tracking-tight sm:text-3xl">
          내일 종가 +2.5% 오를 ETF, AI가 매일 골라드립니다
        </h1>
        <p className="mt-3 max-w-xl text-sm text-indigo-50/90">
          한국 ETF 901개를 매일 KST 08시에 학습해 가능성이 높은 종목만 추천합니다.
        </p>
        {targetDate && (
          <div className="mt-5 flex flex-wrap items-center gap-2 text-xs">
            <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-3 py-1 font-semibold backdrop-blur">
              예측 대상일 · {formatKoreanDate(targetDate)}
            </span>
            <span className="text-indigo-100">
              오늘 추천 <strong className="text-white">{recommendedCount}건</strong>
              {empiricalPrecision != null && (
                <>
                  {" "}· 누적 정밀도{" "}
                  <strong className="text-white">
                    {pct(empiricalPrecision, 1)}
                  </strong>{" "}
                  ({totalResolved}건 검증)
                </>
              )}
            </span>
          </div>
        )}
      </div>
    </section>
  );
}

function PicksGrid({
  picks,
}: {
  picks: Awaited<ReturnType<typeof fetchLatestPicks>>["picks"];
}) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {picks.map((p) => (
        <Link key={p.symbol} href={`/etf/${p.symbol}`} className="group">
          <Card className="transition group-hover:border-indigo-400 group-hover:shadow-md">
            <CardContent className="flex items-center justify-between gap-4 p-4">
              <div className="min-w-0">
                <div className="font-mono text-[11px] text-slate-400">
                  {p.symbol}
                </div>
                <div className="truncate text-base font-semibold text-slate-900 group-hover:text-indigo-600">
                  {p.name}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="default" className="text-sm font-bold">
                  {pct(p.probability, 1)}
                </Badge>
                <ArrowUpRight className="h-4 w-4 text-slate-400 transition group-hover:text-indigo-500" />
              </div>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}

function FallbackBlock({
  items,
  date,
}: {
  items: NonNullable<
    Awaited<ReturnType<typeof fetchLatestModelMetrics>>
  >["fallback_picks_json"];
  date: string | null;
}) {
  return (
    <div className="space-y-3">
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-xs dark:border-amber-500/30 dark:bg-amber-500/10">
        <p className="font-semibold text-amber-900 dark:text-amber-200">
          {formatKoreanDate(date)} · 추천 기준선(70%) 통과 종목 없음
        </p>
        <p className="mt-1 text-amber-800 dark:text-amber-200/80">
          아래는 참고용으로만 제공되는 후보입니다 · 검증 기록 미포함
        </p>
      </div>
      {(items ?? []).map((p) => (
        <Card key={p.symbol} className="overflow-hidden">
          <Link
            href={`/etf/${p.symbol}`}
            className="flex items-center justify-between gap-4 border-b border-slate-100 p-4 transition hover:bg-indigo-50/40 dark:border-slate-800 dark:hover:bg-slate-800/40"
          >
            <div className="min-w-0">
              <div className="font-mono text-[11px] text-slate-400">
                {p.symbol}
              </div>
              <div className="truncate font-semibold">{p.name}</div>
            </div>
            <div className="text-right">
              <div className="text-sm font-bold text-amber-700 dark:text-amber-400">
                {pct(p.probability, 1)}
              </div>
              <div className="text-[10px] text-slate-500">
                정밀도 {pct(p.precision_band, 1)}
              </div>
            </div>
          </Link>
          {p.news_json && p.news_json.length > 0 && (
            <div className="grid gap-2 p-4">
              <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                관련 기사
              </div>
              {p.news_json.slice(0, 3).map((a, i) => (
                <a
                  key={i}
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block rounded-lg border border-slate-200 bg-white p-2.5 text-sm transition hover:border-indigo-400 hover:bg-indigo-50/40 dark:border-slate-700 dark:bg-slate-800 dark:hover:border-indigo-500"
                >
                  <div className="text-[11px] text-slate-500">
                    {a.source && (
                      <span className="rounded-full bg-slate-100 px-1.5 py-0.5 font-semibold dark:bg-slate-700">
                        {a.source}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 line-clamp-2 text-[13px] font-medium">
                    {a.title}
                  </div>
                </a>
              ))}
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}

function EmptyPicks({ date }: { date: string | null }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
        <div className="rounded-full bg-slate-100 p-3 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
          <ChartLine className="h-5 w-5" />
        </div>
        <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
          {date ? `${formatKoreanDate(date)} ` : ""}추천할 종목이 없습니다.
        </p>
        <p className="max-w-sm text-xs text-slate-500 dark:text-slate-400">
          모델은 모든 한국 ETF에 대해 상승 확률을 계산했지만, 추천 기준선(70%)을
          넘는 종목이 없었습니다. 시장이 잠잠한 날이라는 뜻입니다.
        </p>
      </CardContent>
    </Card>
  );
}

