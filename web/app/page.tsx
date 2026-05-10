import Link from "next/link";
import { ArrowUpRight, ChartLine, FileText, Newspaper } from "lucide-react";
import {
  fetchLatestModelMetrics,
  fetchLatestPicks,
  fetchResolvedHistory,
} from "@/lib/queries";
import { formatKoreanDate, pct } from "@/lib/format";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatTile } from "@/components/ui/stat-tile";
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
            <p className="mt-0.5 text-sm text-slate-500">
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
            <p className="mt-0.5 text-sm text-slate-500">
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

      <section>
        <h2 className="mb-4 text-lg font-bold tracking-tight">자세히 보기</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <NavCard
            href="/today"
            title="오늘 상세"
            desc="추천 종목 카드 + 관련 기사"
            icon={Newspaper}
          />
          <NavCard
            href="/backtest"
            title="수익률 시뮬레이션"
            desc="모델 vs 시장 비교"
            icon={ChartLine}
          />
          <NavCard
            href="/model"
            title="모델 정보"
            desc="피처와 정밀도 곡선"
            icon={FileText}
          />
        </div>
      </section>
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
    <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-600 via-indigo-700 to-violet-700 px-6 py-10 text-white shadow-xl shadow-indigo-500/25 sm:px-10 sm:py-14">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(255,255,255,0.18),_transparent_60%)]" />
      <div className="relative">
        <div className="text-[10.5px] font-semibold uppercase tracking-[0.18em] text-indigo-100">
          Korean ETF · Daily Signal
        </div>
        <h1 className="mt-3 max-w-3xl text-3xl font-bold leading-tight tracking-tight sm:text-4xl">
          내일 종가 +2.5% 오를 ETF,
          <br className="hidden sm:block" />
          AI가 매일 골라드립니다
        </h1>
        <p className="mt-4 max-w-2xl text-sm text-indigo-50/95 sm:text-base">
          한국 ETF 901개를 매일 KST 08시에 학습해, 다음 거래일 종가가 직전
          거래일 대비 +2.5% 이상 오를 가능성이 높은 종목만을 골라냅니다.
        </p>
        {targetDate && (
          <div className="mt-6 inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-xs font-semibold backdrop-blur">
            예측 대상일 · {formatKoreanDate(targetDate)}
          </div>
        )}
        <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4">
          <HeroStat
            label="오늘 추천"
            value={`${recommendedCount}건`}
          />
          <HeroStat
            label="누적 검증"
            value={`${totalResolved}건`}
          />
          <HeroStat
            label="경험적 정밀도"
            value={
              empiricalPrecision == null ? "—" : pct(empiricalPrecision, 1)
            }
            className="hidden sm:block"
          />
        </div>
      </div>
    </section>
  );
}

function HeroStat({
  label,
  value,
  className,
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div
      className={`rounded-2xl border border-white/20 bg-white/10 px-4 py-3 backdrop-blur ${className ?? ""}`}
    >
      <div className="text-[10.5px] font-medium uppercase tracking-wider text-indigo-100">
        {label}
      </div>
      <div className="mt-1 text-xl font-bold tabular-nums text-white">{value}</div>
    </div>
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
    <Card className="border-amber-200 bg-amber-50">
      <CardHeader>
        <CardTitle className="text-amber-900">
          {formatKoreanDate(date)} · 추천 기준선(70%) 통과 종목 없음
        </CardTitle>
        <CardDescription className="text-amber-800">
          참고용으로만 제공되는 모델이 그래도 가장 가능성을 높게 본 종목입니다.
          정밀도가 낮은 구간이므로 다른 정보와 함께 검토하세요. 검증 기록에
          누적되지 않습니다.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {(items ?? []).map((p) => (
          <Link
            key={p.symbol}
            href={`/etf/${p.symbol}`}
            className="flex items-center justify-between rounded-lg bg-white/80 px-3 py-2.5 text-sm transition hover:bg-white"
          >
            <span className="font-medium">
              {p.symbol} · {p.name}
            </span>
            <span className="text-xs text-slate-600">
              확률 {pct(p.probability, 1)} · 정밀도 {pct(p.precision_band, 1)}
            </span>
          </Link>
        ))}
      </CardContent>
    </Card>
  );
}

function EmptyPicks({ date }: { date: string | null }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
        <div className="rounded-full bg-slate-100 p-3 text-slate-500">
          <ChartLine className="h-5 w-5" />
        </div>
        <p className="text-sm font-semibold text-slate-700">
          {date ? `${formatKoreanDate(date)} ` : ""}추천할 종목이 없습니다.
        </p>
        <p className="max-w-sm text-xs text-slate-500">
          모델은 모든 한국 ETF에 대해 상승 확률을 계산했지만, 추천 기준선(70%)을
          넘는 종목이 없었습니다. 시장이 잠잠한 날이라는 뜻입니다.
        </p>
      </CardContent>
    </Card>
  );
}

function NavCard({
  href,
  title,
  desc,
  icon: Icon,
}: {
  href: string;
  title: string;
  desc: string;
  icon: React.ElementType;
}) {
  return (
    <Link href={href} className="group">
      <Card className="h-full transition group-hover:-translate-y-0.5 group-hover:border-indigo-400 group-hover:shadow-md">
        <CardContent className="flex items-start gap-3 p-4">
          <div className="rounded-lg bg-indigo-50 p-2 text-indigo-600">
            <Icon className="h-4 w-4" />
          </div>
          <div className="flex-1">
            <div className="text-sm font-semibold text-slate-900">{title}</div>
            <div className="mt-0.5 text-xs text-slate-500">{desc}</div>
          </div>
          <ArrowUpRight className="h-4 w-4 text-slate-400 transition group-hover:text-indigo-500" />
        </CardContent>
      </Card>
    </Link>
  );
}
