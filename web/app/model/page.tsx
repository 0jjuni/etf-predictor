import Link from "next/link";
import { fetchLatestModelMetrics } from "@/lib/queries";
import { formatKoreanDate, pct } from "@/lib/format";
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
      <nav className="text-xs text-slate-500">
        <Link href="/" className="hover:underline">
          홈
        </Link>{" "}
        / 모델 정보
      </nav>

      <header>
        <h1 className="text-2xl font-bold">모델 정보</h1>
        <p className="mt-2 text-sm text-slate-600">
          한국 ETF 중에서 다음 거래일 종가가 +2.5% 이상 오를 가능성이 높은
          종목을 매일 자동으로 골라줍니다.
        </p>
      </header>

      <section className="rounded-2xl border border-slate-200 bg-white p-5">
        <h2 className="text-lg font-semibold">모델은 무엇을 보나요?</h2>
        <ul className="mt-3 space-y-3 text-sm text-slate-700">
          <li>
            <strong>가격이 매일 얼마나 움직였는지</strong> — 일간 변동률(Change)
          </li>
          <li>
            <strong>시장이 과열·과냉되었는지</strong> — RSI(14). 70 이상은
            과매수, 30 미만은 과매도로 일반적으로 해석되는 모멘텀 지표
          </li>
          <li>
            <strong>추세가 강해지고 있는지</strong> — 모멘텀(10). 10거래일 전
            대비 가격 변화량
          </li>
        </ul>
        <p className="mt-3 text-sm text-slate-600">
          최근 100거래일(약 5개월) 데이터를 입력으로 받아, 각 ETF에 대해 0~100%
          상승 확률을 출력합니다. 70% 이상인 종목만 추천 표에 노출돼요.
        </p>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5">
        <h2 className="text-lg font-semibold">왜 정밀도(Precision)에 집중하나요?</h2>
        <p className="mt-2 text-sm text-slate-700">
          실제 투자에 쓸 수 있는 자금은 한정적입니다. 그래서 이 모델은 &ldquo;많이
          맞히는 것&rdquo;보다 <strong>맞힌다고 한 것을 정확히 맞히는 것</strong>
          을 우선합니다. 결과적으로 놓치는 상승 종목 수는 늘어나지만(재현율
          하락), 추천된 종목 하나하나의 적중률은 더 신뢰할 만한 수준이 됩니다.
          &ldquo;오늘 추천 없음&rdquo;인 날이 정상적으로 자주 발생합니다.
        </p>
      </section>

      {m && (
        <section className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="text-lg font-semibold">최근 학습 메트릭</h2>
          <div className="mt-3 grid grid-cols-3 gap-3">
            <Stat label="학습일" value={formatKoreanDate(m.target_date)} />
            <Stat
              label="검증 샘플"
              value={m.test_size.toLocaleString("ko-KR")}
            />
            <Stat label="실제 상승 비율" value={pct(m.positive_rate, 2)} />
          </div>
          <p className="mt-3 text-xs text-slate-500">
            검증 샘플 중 실제 +2.5% 상승한 비율이 약 4%로 매우 적습니다. 그래서
            모델은 70% 이상이라는 높은 기준으로 정밀도를 우선합니다.
          </p>

          <h3 className="mt-6 text-base font-semibold">임계값 곡선</h3>
          <p className="mt-1 text-xs text-slate-500">
            임계값을 올릴수록 후보 수는 줄지만 정밀도는 일반적으로 올라갑니다.
          </p>
          <ThresholdChart curve={m.metrics_json} />
        </section>
      )}

      <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
        <h2 className="text-base font-semibold text-amber-900">유의사항</h2>
        <ul className="mt-2 space-y-1.5 text-xs text-amber-900">
          <li>모델은 과거 패턴 기반이며 시장 급변에는 약합니다</li>
          <li>거래량·시가총액이 작은 ETF는 신호의 신뢰도가 떨어집니다</li>
          <li>합성·레버리지·선물·인버스 ETF는 학습·예측에서 제외됩니다</li>
          <li>본 도구는 투자 판단의 보조 자료이며 매수·매도 권유가 아닙니다</li>
        </ul>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-base font-bold text-slate-800">{value}</div>
    </div>
  );
}
