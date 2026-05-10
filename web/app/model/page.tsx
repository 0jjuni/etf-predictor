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
    "한국 ETF 종가 예측기 모델이 보는 15가지 시그널, 학습 방법, 정밀도 우선 설계, 임계값별 성능 곡선을 공개합니다.",
};

interface FeatureRow {
  group: string;
  items: { name: string; tag: string; desc: string }[];
}

const FEATURE_GROUPS: FeatureRow[] = [
  {
    group: "가격 흐름",
    items: [
      { name: "일간 변동률", tag: "Change", desc: "전일 종가 대비 당일 종가 변동률" },
      { name: "10일 모멘텀", tag: "Momentum", desc: "10거래일 전 대비 가격 변화율 (% 정규화)" },
      { name: "5일 SMA 비율", tag: "SMA5_ratio", desc: "종가 ÷ 5일 이동평균 - 1 (단기 위치)" },
      { name: "20일 SMA 비율", tag: "SMA20_ratio", desc: "종가 ÷ 20일 이동평균 - 1 (중기 위치)" },
    ],
  },
  {
    group: "모멘텀 / 변동성",
    items: [
      { name: "RSI(14)", tag: "RSI", desc: "0~100 사이 모멘텀 지표. 70+ 과매수, 30- 과매도" },
      { name: "스토캐스틱 %K", tag: "Stoch_K", desc: "14일 고저 대비 현재 종가 위치" },
      { name: "MACD 히스토그램", tag: "MACD_hist", desc: "추세 전환 신호. 종가로 정규화" },
      { name: "볼린저 %B", tag: "BB_pctB", desc: "상단/하단 밴드 사이 어디 있는지 (0~1)" },
      { name: "볼린저 밴드폭", tag: "BB_bw", desc: "변동성 확장/수축" },
      { name: "ATR (정규화)", tag: "ATR_norm", desc: "14일 평균 진폭 ÷ 종가" },
    ],
  },
  {
    group: "거래량",
    items: [
      { name: "거래량 비율", tag: "Vol_ratio", desc: "당일 거래량 ÷ 20일 평균 거래량" },
    ],
  },
  {
    group: "시장 맥락",
    items: [
      { name: "KOSPI 200", tag: "Market_KR", desc: "KODEX 200 일간 수익률 — 한국 시장 분위기" },
      { name: "S&P 500", tag: "Market_US500", desc: "미국 대형주 일간 수익률 — 미국 추종 ETF에 결정적" },
      { name: "나스닥", tag: "Market_NASDAQ", desc: "나스닥 컴포지트 일간 수익률 — 기술주 중심 ETF" },
      { name: "원/달러", tag: "Market_USDKRW", desc: "환율 일간 변화 — 미국 ETF 수익률에 영향" },
    ],
  },
];

export default async function ModelPage() {
  const m = await fetchLatestModelMetrics();

  return (
    <div className="space-y-6">
      <nav className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
        <Link href="/" className="hover:text-indigo-600">
          홈
        </Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-700 dark:text-slate-300">모델 정보</span>
      </nav>

      <header>
        <h1 className="text-2xl font-bold tracking-tight">모델 정보</h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
          한국 ETF 중에서 다음 거래일 종가가 +2.5% 이상 오를 가능성이 높은
          종목을 매일 자동으로 골라주는 모델입니다. 무엇을 보고, 어떻게 학습하고,
          왜 신뢰할 수 있는지 투명하게 공개합니다.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>모델은 무엇을 보나요?</CardTitle>
          <CardDescription>
            최근 100거래일(약 5개월) × 15개 시그널 = 1,500차원의 입력으로 다음
            거래일 종가가 +2.5% 이상 오를 확률을 계산합니다.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {FEATURE_GROUPS.map((group) => (
            <div key={group.group}>
              <div className="mb-2 text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                {group.group}
              </div>
              <ul className="grid gap-2 sm:grid-cols-2">
                {group.items.map((f) => (
                  <li
                    key={f.tag}
                    className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-800/40"
                  >
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                        {f.name}
                      </span>
                      <span className="font-mono text-[10px] text-slate-400">
                        {f.tag}
                      </span>
                    </div>
                    <div className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                      {f.desc}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>어떻게 학습하나요?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-700 dark:text-slate-300">
          <div>
            <strong className="text-slate-900 dark:text-slate-100">
              매일 KST 08시 자동 학습
            </strong>{" "}
            — GitHub Actions cron이 한국 ETF 전체의 최신 데이터를 새로 받아
            모델을 처음부터 다시 학습합니다. 합성·레버리지·선물·인버스 ETF는
            가격 메커니즘이 달라서 학습·예측 모두에서 제외됩니다.
          </div>
          <div>
            <strong className="text-slate-900 dark:text-slate-100">
              XGBoost 분류기 + 정규화 강화
            </strong>{" "}
            — 트리 기반 부스팅 모델. 노이즈 많은 금융 데이터에 맞춰 subsample,
            colsample_bytree, gamma, L1/L2 정규화를 보수적으로 설정해
            과적합을 억제합니다.
          </div>
          <div>
            <strong className="text-slate-900 dark:text-slate-100">
              시간 기반 검증 (Walk-forward)
            </strong>{" "}
            — 가장 최근 20% 거래일을 검증용으로 떼어냅니다. 무작위 split이
            아니라 시간 순서대로 나눠야 같은 날의 다른 ETF나 인접 윈도우에서
            오는 누설(leakage)을 제거할 수 있어요.
          </div>
          <div>
            <strong className="text-slate-900 dark:text-slate-100">
              확률 보정 (Isotonic Calibration)
            </strong>{" "}
            — XGBoost가 출력하는 raw 확률을 isotonic regression으로 다시 매핑
            합니다. &ldquo;70% 확률&rdquo;이라고 표시되면 검증 데이터에서 실제로
            약 70% 적중률을 갖도록 보정.
          </div>
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
            <strong className="text-slate-900 dark:text-slate-100">
              맞힌다고 한 것을 정확히 맞히는 것
            </strong>
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
              <strong className="text-slate-900 dark:text-slate-100">70% 이상</strong>으로
              높게 설정
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
          <CardTitle className="text-amber-900 dark:text-amber-200">
            유의사항
          </CardTitle>
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
