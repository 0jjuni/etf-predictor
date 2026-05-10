import Link from "next/link";
import {
  fetchLatestModelMetrics,
  fetchLatestPicks,
} from "@/lib/queries";
import { formatKoreanDate, pct } from "@/lib/format";

export const revalidate = 300;

export const metadata = {
  title: "오늘의 추천",
  description:
    "오늘의 한국 ETF 추천 종목과 모델 추정 상승 확률, 관련 기사 모음",
};

export default async function TodayPage() {
  const [{ targetDate, picks }, metrics] = await Promise.all([
    fetchLatestPicks(),
    fetchLatestModelMetrics(),
  ]);
  const fallback = metrics?.fallback_picks_json ?? [];

  return (
    <div className="space-y-6">
      <nav className="text-xs text-slate-500">
        <Link href="/" className="hover:underline">
          홈
        </Link>{" "}
        / 오늘
      </nav>

      <header>
        <h1 className="text-2xl font-bold">
          {formatKoreanDate(targetDate)} 추천
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          모델이 다음 거래일 종가가 +2.5% 이상 오를 것으로 예측한 종목입니다.
        </p>
      </header>

      {picks.length > 0 ? (
        <section className="space-y-4">
          {picks.map((p) => (
            <article
              key={p.symbol}
              className="rounded-2xl border border-slate-200 bg-white p-5"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <Link
                    href={`/etf/${p.symbol}`}
                    className="font-mono text-xs text-slate-500 hover:underline"
                  >
                    {p.symbol}
                  </Link>
                  <h2 className="mt-1 text-lg font-semibold">
                    <Link
                      href={`/etf/${p.symbol}`}
                      className="hover:text-indigo-600"
                    >
                      {p.name}
                    </Link>
                  </h2>
                </div>
                <div className="rounded-full bg-indigo-50 px-3 py-1 text-sm font-bold text-indigo-700">
                  {pct(p.probability, 1)}
                </div>
              </div>
              {p.news_json && p.news_json.length > 0 && (
                <div className="mt-4 grid gap-2">
                  {p.news_json.map((a, i) => (
                    <a
                      key={i}
                      href={a.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block rounded-lg border border-slate-200 p-3 text-sm transition hover:border-indigo-400 hover:bg-indigo-50"
                    >
                      <div className="text-xs text-slate-500">
                        {a.source} · {formatPubDate(a.published)}
                      </div>
                      <div className="mt-1 font-medium text-slate-800">
                        {a.title}
                      </div>
                    </a>
                  ))}
                </div>
              )}
            </article>
          ))}
        </section>
      ) : fallback.length > 0 ? (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
          <p className="text-sm font-semibold text-amber-900">
            정상 추천 기준선(70%) 통과 종목 없음 — 참고용 후보
          </p>
          <ul className="mt-3 space-y-2 text-sm">
            {fallback.map((p) => (
              <li
                key={p.symbol}
                className="flex items-center justify-between rounded-lg bg-white/80 px-3 py-2"
              >
                <Link
                  href={`/etf/${p.symbol}`}
                  className="font-medium hover:underline"
                >
                  {p.symbol} · {p.name}
                </Link>
                <span className="text-xs text-slate-600">
                  확률 {pct(p.probability, 1)} · 정밀도 {pct(p.precision_band, 1)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 text-center">
          <p className="text-sm font-semibold text-slate-700">
            추천할 종목이 없습니다.
          </p>
          <p className="mt-2 text-xs text-slate-500">
            모델은 모든 한국 ETF에 대해 상승 확률을 계산했지만, 추천 기준선을
            넘는 종목이 없었습니다.
          </p>
        </section>
      )}
    </div>
  );
}

function formatPubDate(raw: string | undefined): string {
  if (!raw) return "";
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw.slice(0, 16);
  return `${d.getMonth() + 1}월 ${d.getDate()}일`;
}
