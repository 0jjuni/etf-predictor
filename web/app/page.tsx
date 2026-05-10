import Link from "next/link";
import {
  fetchLatestModelMetrics,
  fetchLatestPicks,
  fetchResolvedHistory,
} from "@/lib/queries";
import { formatKoreanDate, pct } from "@/lib/format";
import { EquityCurve } from "./_components/EquityCurve";

// Pull fresh data each request; the underlying tables update once a day.
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

  return (
    <div className="space-y-8">
      <Hero targetDate={targetDate} />

      <section className="space-y-4">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-semibold">오늘의 추천</h2>
          {targetDate && (
            <span className="text-xs text-slate-500">
              기준일 {formatKoreanDate(targetDate)}
            </span>
          )}
        </div>

        {hasPicks ? (
          <PicksTable picks={picks} />
        ) : showFallback ? (
          <FallbackBlock items={fallbackPicks} date={targetDate} />
        ) : (
          <EmptyPicks date={targetDate} />
        )}
      </section>

      <SimulationSection history={history} />

      <section className="rounded-2xl border border-slate-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">자세히 보기</h2>
          <Link
            href="/today"
            className="text-sm text-indigo-600 hover:underline"
          >
            전체 기록 →
          </Link>
        </div>
        <p className="mt-2 text-sm text-slate-600">
          모델 카드, 임계값 곡선, 종목별 페이지로 이어집니다.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <NavCard href="/backtest" title="수익률 시뮬레이션" desc="추천대로 샀다면" />
          <NavCard href="/model" title="모델 정보" desc="피처와 정밀도 곡선" />
          <NavCard href="/today" title="오늘 상세" desc="추천 종목 + 뉴스" />
        </div>
      </section>
    </div>
  );
}

function Hero({ targetDate }: { targetDate: string | null }) {
  return (
    <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-700 px-6 py-8 text-white shadow-lg shadow-indigo-500/20">
      <div className="text-xs font-semibold uppercase tracking-wider text-white/85">
        Korean ETF · Daily Signal
      </div>
      <h1 className="mt-2 text-2xl font-bold leading-tight sm:text-3xl">
        다음 거래일 종가 +2.5% 이상 오를 ETF 추천
      </h1>
      <p className="mt-3 max-w-2xl text-sm text-white/90 sm:text-base">
        AI 모델이 매일 KST 08시에 한국 ETF 시장을 학습해, 다음 거래일에 종가가
        직전 거래일 대비 +2.5% 이상 오를 가능성이 높은 종목만을 골라냅니다.
      </p>
      {targetDate && (
        <div className="mt-5 inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-xs font-semibold backdrop-blur">
          예측 대상일 · {formatKoreanDate(targetDate)}
        </div>
      )}
    </section>
  );
}

function PicksTable({ picks }: { picks: Awaited<ReturnType<typeof fetchLatestPicks>>["picks"] }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-slate-500">
          <tr>
            <th className="px-4 py-3 text-left font-semibold">코드</th>
            <th className="px-4 py-3 text-left font-semibold">종목명</th>
            <th className="px-4 py-3 text-right font-semibold">상승확률</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200">
          {picks.map((p) => (
            <tr key={p.symbol} className="hover:bg-indigo-50/40">
              <td className="px-4 py-3 font-mono text-xs text-slate-600">
                <Link className="hover:underline" href={`/etf/${p.symbol}`}>
                  {p.symbol}
                </Link>
              </td>
              <td className="px-4 py-3 font-medium">
                <Link className="hover:text-indigo-600" href={`/etf/${p.symbol}`}>
                  {p.name}
                </Link>
              </td>
              <td className="px-4 py-3 text-right font-semibold text-indigo-600">
                {pct(p.probability, 1)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
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
    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
      <p className="text-sm font-semibold text-amber-900">
        {formatKoreanDate(date)} · 정상 추천 기준선(70%) 통과 종목 없음
      </p>
      <p className="mt-1 text-xs text-amber-800">
        아래는 참고용으로만 제공되는, 모델이 그래도 가장 가능성을 높게 본
        종목입니다. 정밀도가 낮은 구간이므로 다른 정보와 함께 검토하세요. 검증
        기록에 누적되지 않습니다.
      </p>
      <ul className="mt-3 space-y-2">
        {(items ?? []).map((p) => (
          <li
            key={p.symbol}
            className="flex items-center justify-between rounded-lg bg-white/80 px-3 py-2 text-sm"
          >
            <Link href={`/etf/${p.symbol}`} className="font-medium hover:underline">
              {p.symbol} · {p.name}
            </Link>
            <span className="text-xs text-slate-600">
              확률 {pct(p.probability, 1)} · 정밀도 {pct(p.precision_band, 1)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function EmptyPicks({ date }: { date: string | null }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center">
      <p className="text-sm font-semibold text-slate-700">
        {date ? `${formatKoreanDate(date)} ` : ""}추천할 종목이 없습니다.
      </p>
      <p className="mt-2 text-xs text-slate-500">
        모델은 모든 한국 ETF에 대해 상승 확률을 계산했지만, 추천 기준선(70%)을
        넘는 종목이 없었어요. 시장이 잠잠하거나 뚜렷한 모멘텀 신호가 없는 날이
        라는 뜻입니다.
      </p>
    </div>
  );
}

function NavCard({
  href,
  title,
  desc,
}: {
  href: string;
  title: string;
  desc: string;
}) {
  return (
    <Link
      href={href}
      className="block rounded-xl border border-slate-200 bg-slate-50 p-4 transition hover:border-indigo-400 hover:bg-indigo-50"
    >
      <div className="text-sm font-semibold text-slate-800">{title}</div>
      <div className="mt-1 text-xs text-slate-500">{desc}</div>
    </Link>
  );
}

function SimulationSection({
  history,
}: {
  history: Awaited<ReturnType<typeof fetchResolvedHistory>>;
}) {
  if (history.length === 0) {
    return null;
  }
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5">
      <h2 className="text-lg font-semibold">추천대로 샀다면?</h2>
      <p className="mt-1 text-sm text-slate-600">
        매일 추천 종목을 동일 비중으로 매수해 다음 거래일 종가에 매도했다고
        가정 (거래비용·세금 미반영). 추천 없는 날에는 현금 보유.
      </p>
      <EquityCurve history={history} />
    </section>
  );
}
