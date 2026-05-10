import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { fetchLatestModelMetrics } from "@/lib/queries";
import { formatKoreanDate, pct } from "@/lib/format";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatTile } from "@/components/ui/stat-tile";
import { ThresholdChart } from "../_components/ThresholdChart";

export const revalidate = 300;

export const metadata = {
  title: "모델 정보",
  description:
    "ETF 종가 예측기가 어떤 피처를 보고 어떻게 학습하는지, 그리고 임계값별 정밀도/재현율 곡선을 공개합니다.",
};

export default async function ModelPage() {
  const m = await fetchLatestModelMetrics();

  return (
    <div className="space-y-6">
      <nav className="flex items-center gap-1 text-xs text-slate-500">
        <Link href="/" className="hover:text-indigo-600">
          홈
        </Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-700">모델 정보</span>
      </nav>

      <header>
        <h1 className="text-2xl font-bold tracking-tight">모델 정보</h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-500">
          한국 ETF 중에서 다음 거래일 종가가 +2.5% 이상 오를 가능성이 높은
          종목을 매일 자동으로 골라줍니다.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>모델은 무엇을 보나요?</CardTitle>
          <CardDescription>
            최근 100거래일(약 5개월) 동안의 가격 흐름을 세 가지 시그널로 분석합니다.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="grid gap-3 text-sm sm:grid-cols-3">
            <FeatureCard
              title="일간 변동률"
              tag="Change"
              desc="전일 종가 대비 당일 종가의 변동률 — 단기 가격 흐름"
            />
            <FeatureCard
              title="RSI(14)"
              tag="모멘텀 강도"
              desc="0~100 사이 값. 70 이상은 과매수, 30 미만은 과매도로 해석"
            />
            <FeatureCard
              title="모멘텀(10)"
              tag="추세 가속도"
              desc="10거래일 전 종가 대비 변화량 — 중기 추세의 강도"
            />
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>왜 정밀도(Precision)에 집중하나요?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-700 dark:text-slate-300">
          <p>
            실제 투자에 쓸 수 있는 자금은 한정적입니다. 그래서 이 모델은 &ldquo;많이
            맞히는 것&rdquo;보다{" "}
            <strong className="text-slate-900">맞힌다고 한 것을 정확히 맞히는 것</strong>
            을 우선합니다.
          </p>
          <ul className="space-y-1.5">
            <li className="flex gap-2">
              <span className="text-indigo-600">•</span>
              100개 종목 추천하고 30개 적중보다, 5개 추천하고 4개 적중이 실제
              수익에 더 도움
            </li>
            <li className="flex gap-2">
              <span className="text-indigo-600">•</span>
              추천 기준선을 상승 확률{" "}
              <strong className="text-slate-900">70% 이상</strong>으로 높게
              설정
            </li>
            <li className="flex gap-2">
              <span className="text-indigo-600">•</span>
              결과적으로 놓치는 상승 종목 수는 늘어나지만(재현율 하락), 추천된
              종목 하나하나의 적중률은 더 신뢰할 만한 수준
            </li>
            <li className="flex gap-2">
              <span className="text-indigo-600">•</span>
              &ldquo;오늘 추천 없음&rdquo;인 날도 정상입니다 — 신뢰도 낮은 신호를
              억지로 만들지 않는다는 뜻
            </li>
          </ul>
        </CardContent>
      </Card>

      {m && (
        <Card>
          <CardHeader>
            <CardTitle>최근 학습 메트릭</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3">
              <StatTile
                label="학습일"
                value={formatKoreanDate(m.target_date)}
              />
              <StatTile
                label="검증 샘플"
                value={m.test_size.toLocaleString("ko-KR")}
              />
              <StatTile
                label="실제 상승 비율"
                value={pct(m.positive_rate, 2)}
              />
            </div>
            <p className="mt-3 text-xs text-slate-500">
              검증 샘플 중 실제 +2.5% 상승한 비율이 약 4%로 매우 적습니다.
              그래서 모델은 70% 이상이라는 높은 기준으로 정밀도를 우선합니다.
            </p>

            <h3 className="mt-6 text-sm font-bold tracking-tight">임계값 곡선</h3>
            <p className="mt-1 text-xs text-slate-500">
              임계값을 올릴수록 후보 수는 줄지만 정밀도는 일반적으로 올라갑니다.
            </p>
            <ThresholdChart curve={m.metrics_json} />
          </CardContent>
        </Card>
      )}

      <Card className="border-amber-200 bg-amber-50 dark:border-amber-500/30 dark:bg-amber-500/10">
        <CardHeader>
          <CardTitle className="text-amber-900 dark:text-amber-200">유의사항</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-1.5 text-xs text-amber-900 dark:text-amber-200">
            <li>모델은 과거 패턴 기반이며 시장 급변에는 약합니다</li>
            <li>거래량·시가총액이 작은 ETF는 신호의 신뢰도가 떨어집니다</li>
            <li>합성·레버리지·선물·인버스 ETF는 학습·예측에서 제외됩니다</li>
            <li>본 도구는 투자 판단의 보조 자료이며 매수·매도 권유가 아닙니다</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

function FeatureCard({
  title,
  tag,
  desc,
}: {
  title: string;
  tag: string;
  desc: string;
}) {
  return (
    <li className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-800/40">
      <div className="text-[10.5px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
        {tag}
      </div>
      <div className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">
        {title}
      </div>
      <div className="mt-1 text-xs text-slate-600 dark:text-slate-400">{desc}</div>
    </li>
  );
}
