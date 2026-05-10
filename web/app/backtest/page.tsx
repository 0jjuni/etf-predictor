import Link from "next/link";
import { fetchResolvedHistory } from "@/lib/queries";
import { EquityCurve } from "../_components/EquityCurve";

export const revalidate = 300;

export const metadata = {
  title: "수익률 시뮬레이션",
  description:
    "ETF 종가 예측기 모델이 추천한 종목을 매일 동일 비중으로 매수했다면 누적 수익률이 어떻게 됐는지 확인합니다.",
};

export default async function BacktestPage() {
  const history = await fetchResolvedHistory(2000);

  return (
    <div className="space-y-6">
      <nav className="text-xs text-slate-500">
        <Link href="/" className="hover:underline">
          홈
        </Link>{" "}
        / 수익률 시뮬레이션
      </nav>

      <header className="rounded-2xl border border-slate-200 bg-white p-5">
        <h1 className="text-2xl font-bold">추천대로 샀다면?</h1>
        <p className="mt-2 text-sm text-slate-600">
          매일 모델이 추천한 종목을 동일 비중으로 매수해 다음 거래일 종가에
          매도했다고 가정한 누적 자산 가치 곡선입니다. 추천이 없는 날에는 현금
          보유(수익 0%)로 가정. 거래비용·세금 미반영.
        </p>
      </header>

      {history.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center">
          <p className="text-sm font-semibold text-slate-700">
            검증 가능한 기록이 아직 없습니다.
          </p>
          <p className="mt-2 text-xs text-slate-500">
            매일 학습이 누적되거나 백필을 한 번 돌리면 채워집니다. 정밀도 우선
            설계상 추천 자체가 드물 수 있어요.
          </p>
        </div>
      ) : (
        <section className="rounded-2xl border border-slate-200 bg-white p-5">
          <EquityCurve history={history} />
        </section>
      )}
    </div>
  );
}
