import Link from "next/link";
import { ChevronRight, Newspaper } from "lucide-react";
import {
  fetchLatestModelMetrics,
  fetchLatestPicks,
} from "@/lib/queries";
import { formatKoreanDate, pct } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

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
      <Breadcrumbs />

      <header>
        <h1 className="text-2xl font-bold tracking-tight">
          {formatKoreanDate(targetDate)} 추천
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          모델이 다음 거래일 종가가 +2.5% 이상 오를 것으로 예측한 종목입니다.
        </p>
      </header>

      {picks.length > 0 ? (
        <section className="space-y-4">
          {picks.map((p) => (
            <PickCard
              key={p.symbol}
              symbol={p.symbol}
              name={p.name}
              probability={p.probability}
              articles={p.news_json ?? []}
            />
          ))}
        </section>
      ) : fallback.length > 0 ? (
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="space-y-3 p-5">
            <p className="text-sm font-semibold text-amber-900">
              정상 추천 기준선(70%) 통과 종목 없음 — 참고용 후보
            </p>
            <ul className="space-y-2 text-sm">
              {fallback.map((p) => (
                <li
                  key={p.symbol}
                  className="flex items-center justify-between rounded-lg bg-white/80 px-3 py-2.5"
                >
                  <Link
                    href={`/etf/${p.symbol}`}
                    className="font-medium hover:underline"
                  >
                    {p.symbol} · {p.name}
                  </Link>
                  <span className="text-xs text-slate-600">
                    확률 {pct(p.probability, 1)} · 정밀도{" "}
                    {pct(p.precision_band, 1)}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-sm font-semibold text-slate-700">
              추천할 종목이 없습니다.
            </p>
            <p className="mt-2 text-xs text-slate-500">
              추천 기준선을 넘는 종목이 없었습니다.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function PickCard({
  symbol,
  name,
  probability,
  articles,
}: {
  symbol: string;
  name: string;
  probability: number;
  articles: { title: string; url: string; source: string; published: string }[];
}) {
  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between gap-4 border-b border-slate-100 p-5">
        <div className="min-w-0">
          <Link
            href={`/etf/${symbol}`}
            className="block font-mono text-xs text-slate-400 hover:underline"
          >
            {symbol}
          </Link>
          <Link
            href={`/etf/${symbol}`}
            className="mt-1 block truncate text-lg font-semibold tracking-tight hover:text-indigo-600"
          >
            {name}
          </Link>
        </div>
        <Badge variant="default" className="text-sm font-bold">
          {pct(probability, 1)}
        </Badge>
      </div>

      {articles.length > 0 ? (
        <div className="grid gap-2 p-5">
          <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
            <Newspaper className="h-3.5 w-3.5" />
            관련 기사
          </div>
          {articles.map((a, i) => (
            <a
              key={i}
              href={a.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block rounded-lg border border-slate-200 bg-white p-3 text-sm transition hover:border-indigo-400 hover:bg-indigo-50/40"
            >
              <div className="text-[11px] text-slate-500">
                {a.source && (
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 font-semibold text-slate-700">
                    {a.source}
                  </span>
                )}
                {a.published && (
                  <span className="ml-2">{formatPubDate(a.published)}</span>
                )}
              </div>
              <div className="mt-1.5 font-medium text-slate-800">{a.title}</div>
            </a>
          ))}
        </div>
      ) : null}
    </Card>
  );
}

function formatPubDate(raw: string | undefined): string {
  if (!raw) return "";
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw.slice(0, 16);
  return `${d.getMonth() + 1}월 ${d.getDate()}일`;
}

function Breadcrumbs() {
  return (
    <nav className="flex items-center gap-1 text-xs text-slate-500">
      <Link href="/" className="hover:text-indigo-600">
        홈
      </Link>
      <ChevronRight className="h-3 w-3" />
      <span className="text-slate-700">오늘</span>
    </nav>
  );
}
