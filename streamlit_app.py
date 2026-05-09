"""Streamlit entry point for HuggingFace Spaces.

Reads predictions, the holdout precision curve, and resolved-outcome history
from Supabase. No retraining or live inference happens here.
"""
from __future__ import annotations

import bisect

import pandas as pd
import streamlit as st

from app.db import (
    fetch_history_for,
    fetch_latest_model_metrics,
    fetch_latest_predictions,
    fetch_resolved_history,
)

st.set_page_config(
    page_title="한국 ETF 예측기",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)

st.title("한국 ETF 다음날 2.5% 상승 예측")
st.caption("매일 KST 08:00에 모델을 재학습하여 결과를 저장합니다.")


@st.cache_data(ttl=300)
def _latest_predictions() -> pd.DataFrame:
    return pd.DataFrame(fetch_latest_predictions(limit=200))


@st.cache_data(ttl=300)
def _latest_metrics() -> dict | None:
    return fetch_latest_model_metrics()


@st.cache_data(ttl=300)
def _history(symbol: str) -> pd.DataFrame:
    return pd.DataFrame(fetch_history_for(symbol, limit=60))


@st.cache_data(ttl=300)
def _resolved_history() -> pd.DataFrame:
    return pd.DataFrame(fetch_resolved_history(limit=500))


def _precision_for_prob(prob: float, curve: list[dict]) -> float | None:
    """Highest threshold the prob crosses → that threshold's precision."""
    sorted_curve = sorted(curve, key=lambda r: r["threshold"])
    thresholds = [r["threshold"] for r in sorted_curve]
    idx = bisect.bisect_right(thresholds, prob) - 1
    if idx < 0:
        return None
    return sorted_curve[idx]["precision"]


def _curve_df(curve: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(curve)
    df["threshold"] = df["threshold"].astype(float)
    for col in ("precision", "recall", "f1"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("threshold").reset_index(drop=True)


preds_df = _latest_predictions()
metrics = _latest_metrics()
hist_df = _resolved_history()

tab_picks, tab_history, tab_model = st.tabs(["오늘의 추천", "이력", "모델 정보"])

# --------------------------------------------------------------------------- #
# Tab 1 — Today's picks
# --------------------------------------------------------------------------- #
with tab_picks:
    if preds_df.empty:
        st.warning("아직 저장된 예측이 없어요. 첫 학습 잡이 실행되면 표시됩니다.")
    else:
        target_date = preds_df["target_date"].iloc[0]
        st.subheader(f"기준일: {target_date}  ·  추천 종목 {len(preds_df)}개")

        view = preds_df[["symbol", "name", "probability", "rise_threshold"]].copy()
        view["probability"] = (view["probability"] * 100).round(2)
        view["rise_threshold"] = ((view["rise_threshold"] - 1) * 100).round(2)
        view.columns = ["종목코드", "종목명", "상승확률(%)", "기준상승률(%)"]

        if metrics is not None:
            curve = metrics["metrics_json"]
            band_prec = preds_df["probability"].apply(
                lambda p: _precision_for_prob(float(p), curve)
            )
            view["테스트셋 정밀도(%)"] = (band_prec * 100).round(1)
        else:
            view["테스트셋 정밀도(%)"] = None
            st.info("모델 메트릭이 아직 적재되지 않았습니다 — 다음 학습 후 정밀도가 채워집니다.")

        st.dataframe(view, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("종목별 추천 이력")
        choice = st.selectbox(
            "종목 선택",
            options=preds_df["symbol"].tolist(),
            format_func=lambda s: (
                f"{s} {preds_df.loc[preds_df['symbol'] == s, 'name'].iloc[0]}"
            ),
        )
        sym_hist = _history(choice)
        if sym_hist.empty:
            st.info("이력이 없어요.")
        else:
            sym_hist["probability"] = (sym_hist["probability"] * 100).round(2)
            st.line_chart(sym_hist.set_index("target_date")["probability"])
            st.dataframe(
                sym_hist[["target_date", "probability"]].rename(
                    columns={"target_date": "날짜", "probability": "확률(%)"}
                ),
                use_container_width=True,
                hide_index=True,
            )

# --------------------------------------------------------------------------- #
# Tab 2 — Resolved history with empirical hit rate
# --------------------------------------------------------------------------- #
with tab_history:
    if hist_df.empty:
        st.warning(
            "해결된 예측 이력이 아직 없습니다. 백필을 돌렸거나 매일 학습이 며칠 누적되면 채워집니다."
        )
    else:
        c1, c2, c3 = st.columns(3)
        n = len(hist_df)
        hits = int(hist_df["outcome"].sum())
        c1.metric("누적 추천", f"{n:,}건")
        c2.metric("적중", f"{hits:,}건")
        c3.metric("경험적 정밀도", f"{(hits / n * 100):.1f}%" if n else "—")

        st.markdown(
            "**경험적 정밀도** — 실제로 다음 거래일에 +2.5% 이상 상승한 비율. "
            "테스트셋 정밀도가 모델의 예상치라면, 이 값은 실제 운용 결과예요."
        )

        # Aggregate by date
        by_date = (
            hist_df.groupby("target_date")
            .agg(
                추천수=("symbol", "count"),
                적중=("outcome", "sum"),
                평균확률=("probability", "mean"),
                평균실제변동=("actual_change", "mean"),
            )
            .sort_values("target_date", ascending=False)
            .reset_index()
        )
        by_date["적중률(%)"] = (by_date["적중"] / by_date["추천수"] * 100).round(1)
        by_date["평균확률(%)"] = (by_date["평균확률"] * 100).round(2)
        by_date["평균실제변동(%)"] = (by_date["평균실제변동"] * 100).round(2)
        by_date = by_date.drop(columns=["평균확률", "평균실제변동"])
        by_date.columns = ["날짜", "추천수", "적중", "적중률(%)", "평균확률(%)", "평균실제변동(%)"]

        st.subheader("날짜별 요약")
        st.dataframe(by_date, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("추천 종목 상세 (최근 순)")
        detail = hist_df[
            [
                "target_date",
                "symbol",
                "name",
                "probability",
                "actual_change",
                "outcome",
            ]
        ].copy()
        detail["probability"] = (detail["probability"] * 100).round(2)
        detail["actual_change"] = (detail["actual_change"] * 100).round(2)
        detail["outcome"] = detail["outcome"].map({True: "✓ 적중", False: "✗ 실패"})
        detail.columns = ["날짜", "종목코드", "종목명", "예측확률(%)", "실제변동(%)", "결과"]
        st.dataframe(detail, use_container_width=True, hide_index=True)

# --------------------------------------------------------------------------- #
# Tab 3 — Model card
# --------------------------------------------------------------------------- #
with tab_model:
    if metrics is None:
        st.warning("모델 메트릭이 아직 없습니다. 학습이 한 번 이상 완료되어야 합니다.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("학습일 (target_date)", metrics["target_date"])
        c2.metric("테스트 샘플 수", f"{metrics['test_size']:,}")
        c3.metric("양성 비율", f"{metrics['positive_rate'] * 100:.2f}%")

        st.markdown(
            """
            **읽는 법** — 임계값 T에서의 *Precision*은 "확률이 T 이상인
            예측만 채택했을 때 실제로 +2.5% 상승할 비율"입니다. T를 올릴수록
            대상 후보 수(support)는 줄지만 정밀도는 일반적으로 올라갑니다.
            추천 탭의 "테스트셋 정밀도(%)" 컬럼은 각 종목 확률이 속한 밴드의
            precision을 그대로 가져온 값이에요.
            """
        )

        df = _curve_df(metrics["metrics_json"])

        st.subheader("임계값 곡선")
        st.line_chart(
            df.set_index("threshold")[["precision", "recall", "f1"]],
            height=320,
        )

        show = df.copy()
        show["threshold"] = show["threshold"].map(lambda v: f"{v:.2f}")
        for col in ("precision", "recall", "f1"):
            show[col] = (show[col] * 100).round(2)
        show.columns = [
            "임계값",
            "정밀도(%)",
            "재현율(%)",
            "F1(%)",
            "전체 후보수",
            "양성 후보수",
        ]
        st.dataframe(show, use_container_width=True, hide_index=True)

        st.caption(
            "데이터: 학습 시 stratified 80/20 split의 holdout 셋. "
            "Precision은 cumulative — proba ≥ T인 표본 전체에서 계산."
        )
