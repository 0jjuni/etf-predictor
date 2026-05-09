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
    page_title="ETF 종가 예측기",
    page_icon=":chart_with_upwards_trend:",
    layout="centered",
)

# Light visual polish: tighten the default top padding and harmonize headings.
st.markdown(
    """
    <style>
      .block-container { padding-top: 2rem; padding-bottom: 4rem; }
      h1 { font-size: 1.8rem; font-weight: 700; }
      h2 { font-size: 1.3rem; }
      h3 { font-size: 1.05rem; }
      [data-testid="stMetricLabel"] { font-size: 0.85rem; }
      [data-testid="stMetricValue"] { font-size: 1.4rem; }
      .small-caption { color: #64748b; font-size: 0.85rem; line-height: 1.4; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("ETF 종가 예측기")
st.markdown(
    "<div class='small-caption'>"
    "한국 ETF의 <b>다음 거래일 종가</b>가 직전 거래일 종가 대비 "
    "<b>+2.5% 이상</b> 상승할 가능성이 높은 종목을 추천합니다. "
    "매일 KST 08:00에 모델이 자동으로 재학습됩니다."
    "</div>",
    unsafe_allow_html=True,
)
st.write("")  # spacing


# --------------------------------------------------------------------------- #
# Data loaders
# --------------------------------------------------------------------------- #
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

tab_picks, tab_history, tab_model = st.tabs(["추천 종목", "검증 기록", "모델 정보"])

# --------------------------------------------------------------------------- #
# Tab 1 — Today's picks
# --------------------------------------------------------------------------- #
with tab_picks:
    if preds_df.empty:
        st.warning("아직 저장된 예측이 없습니다. 첫 학습 잡 이후 표시됩니다.")
    else:
        target_date = preds_df["target_date"].iloc[0]
        st.subheader(f"기준일 {target_date}  ·  {len(preds_df)}개 후보")
        st.caption("기준일 종가가 직전 거래일 종가 대비 +2.5% 이상 상승할 가능성으로 정렬됩니다.")

        view = preds_df[["symbol", "name", "probability"]].copy()
        view["probability"] = (view["probability"] * 100).round(1)

        if metrics is not None:
            curve = metrics["metrics_json"]
            band_prec = preds_df["probability"].apply(
                lambda p: _precision_for_prob(float(p), curve)
            )
            view["precision_band"] = (band_prec * 100).round(1)
            view.columns = ["코드", "종목명", "상승확률", "예상정밀도"]
            st.dataframe(
                view,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "코드": st.column_config.TextColumn(width="small"),
                    "종목명": st.column_config.TextColumn(width="medium"),
                    "상승확률": st.column_config.ProgressColumn(
                        format="%.1f%%", min_value=0, max_value=100
                    ),
                    "예상정밀도": st.column_config.NumberColumn(
                        help="이 확률대 종목들이 테스트셋에서 실제로 +2.5% 상승한 비율",
                        format="%.1f%%",
                    ),
                },
            )
        else:
            view.columns = ["코드", "종목명", "상승확률"]
            st.dataframe(view, use_container_width=True, hide_index=True)
            st.info("모델 메트릭이 아직 적재되지 않았습니다 — 다음 학습 후 정밀도가 채워집니다.")

        st.divider()
        st.subheader("관련 기사")
        st.caption("학습 시점의 Google News 검색 결과(KR). 보조 자료로만 활용하세요.")
        any_news = False
        for _, row in preds_df.iterrows():
            articles = row.get("news_json") or []
            if not articles:
                continue
            any_news = True
            with st.expander(f"{row['symbol']}  ·  {row['name']}"):
                for a in articles:
                    src = f"  ·  *{a['source']}*" if a.get("source") else ""
                    pub = f"  ·  {a['published'][:16]}" if a.get("published") else ""
                    st.markdown(f"- [{a['title']}]({a['url']}){src}{pub}")
        if not any_news:
            st.info("아직 적재된 기사 데이터가 없습니다 — 다음 학습 후 채워집니다.")

        st.divider()
        st.subheader("종목별 추천 이력")
        choice = st.selectbox(
            "종목",
            options=preds_df["symbol"].tolist(),
            format_func=lambda s: (
                f"{s} {preds_df.loc[preds_df['symbol'] == s, 'name'].iloc[0]}"
            ),
            label_visibility="collapsed",
        )
        sym_hist = _history(choice)
        if sym_hist.empty:
            st.info("이 종목의 추천 이력이 아직 없습니다.")
        else:
            sym_hist["probability"] = (sym_hist["probability"] * 100).round(2)
            st.line_chart(
                sym_hist.set_index("target_date")["probability"],
                height=240,
                use_container_width=True,
            )

# --------------------------------------------------------------------------- #
# Tab 2 — Resolved history with empirical hit rate
# --------------------------------------------------------------------------- #
with tab_history:
    if hist_df.empty:
        st.warning(
            "검증된 예측 이력이 아직 없습니다. 백필을 돌렸거나 매일 학습이 며칠 누적되면 채워집니다."
        )
    else:
        n = len(hist_df)
        hits = int(hist_df["outcome"].sum())
        rate = (hits / n * 100) if n else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("누적 추천", f"{n:,}")
        c2.metric("실제 적중", f"{hits:,}")
        c3.metric("경험적 정밀도", f"{rate:.1f}%")

        st.markdown(
            "<div class='small-caption'>"
            "<b>경험적 정밀도</b>는 추천했던 종목이 실제로 다음 거래일에 +2.5% 이상 "
            "상승한 비율입니다. 모델이 과거 패턴에서 추정한 <b>예상 정밀도</b>가 "
            "실제 시장에서 어느 정도 재현되는지 보여주는 지표예요."
            "</div>",
            unsafe_allow_html=True,
        )

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
        by_date["적중률"] = (by_date["적중"] / by_date["추천수"] * 100).round(1)
        by_date["평균확률"] = (by_date["평균확률"] * 100).round(1)
        by_date["평균실제변동"] = (by_date["평균실제변동"] * 100).round(2)
        by_date.columns = ["날짜", "추천수", "적중", "평균확률(%)", "평균변동(%)", "적중률(%)"]
        by_date = by_date[["날짜", "추천수", "적중", "적중률(%)", "평균확률(%)", "평균변동(%)"]]

        st.subheader("날짜별 요약")
        st.dataframe(by_date, use_container_width=True, hide_index=True)

        st.subheader("추천 상세")
        detail = hist_df[
            ["target_date", "symbol", "name", "probability", "actual_change", "outcome"]
        ].copy()
        detail["probability"] = (detail["probability"] * 100).round(1)
        detail["actual_change"] = (detail["actual_change"] * 100).round(2)
        detail["outcome"] = detail["outcome"].map({True: "적중", False: "실패"})
        detail.columns = ["날짜", "코드", "종목명", "예측확률(%)", "실제변동(%)", "결과"]
        st.dataframe(detail, use_container_width=True, hide_index=True)

# --------------------------------------------------------------------------- #
# Tab 3 — Model card
# --------------------------------------------------------------------------- #
with tab_model:
    st.subheader("무엇을 예측하나요")
    st.markdown(
        """
        - **타깃**: 한국에 상장된 ETF의 **다음 거래일 종가**가 직전 거래일 종가 대비 **+2.5% 이상** 상승할 확률
        - **단위**: 일 단위 (intraday 시그널 아님)
        - **제외 대상**: 합성·레버리지·선물·인버스 ETF (가격 메커니즘이 일반 ETF와 다름)
        - **추천 기준**: 상승 확률 0.70 이상인 종목만 추천 표에 노출
        """
    )

    st.subheader("입력 피처")
    st.markdown(
        """
        모델은 **최근 100거래일** 동안의 일별 시그널 3종을 보고 다음 거래일을 예측합니다.

        - **일간 변동률 (`Change`)**: 전일 종가 대비 당일 종가 변동률. 단기 가격 흐름을 그대로 반영
        - **RSI(14)**: 14일 상대강도지수. 0~100 사이 값으로, 통상 70 이상은 과매수·30 이하는 과매도로 해석되는 모멘텀 지표
        - **모멘텀(10)**: 10거래일 전 종가 대비 당일 종가의 변동량. 중기 추세의 가속도/감속도 측정
        """
    )

    st.subheader("학습 방법")
    st.markdown(
        """
        - **모델**: XGBoost 이진 분류기 (그래디언트 부스팅 트리)
        - **학습 주기**: 매일 KST 08:00에 GitHub Actions cron이 전체 ETF 데이터를 새로 받아 재학습
        - **검증**: 학습 시 80/20 stratified split의 holdout 셋으로 임계값별 정밀도/재현율을 측정해 함께 저장
        """
    )

    if metrics is None:
        st.info("모델 메트릭이 아직 없습니다. 학습이 한 번 이상 완료되어야 합니다.")
    else:
        st.subheader("최근 학습 메트릭")
        c1, c2, c3 = st.columns(3)
        c1.metric("학습일", metrics["target_date"])
        c2.metric("테스트 샘플", f"{metrics['test_size']:,}")
        c3.metric("양성 비율", f"{metrics['positive_rate'] * 100:.2f}%")

        df = _curve_df(metrics["metrics_json"])

        st.markdown(
            "<div class='small-caption'>"
            "임계값 T에서의 <b>Precision</b>은 \"확률이 T 이상인 예측만 채택했을 때 "
            "실제로 +2.5% 상승할 비율\"입니다. T를 올릴수록 후보 수(Support)는 줄지만 "
            "정밀도는 일반적으로 올라갑니다."
            "</div>",
            unsafe_allow_html=True,
        )
        st.line_chart(
            df.set_index("threshold")[["precision", "recall", "f1"]],
            height=280,
            use_container_width=True,
        )

        with st.expander("임계값별 표 보기"):
            show = df.copy()
            show["threshold"] = show["threshold"].map(lambda v: f"{v:.2f}")
            for col in ("precision", "recall", "f1"):
                show[col] = (show[col] * 100).round(2)
            show.columns = ["임계값", "정밀도(%)", "재현율(%)", "F1(%)", "후보수", "양성수"]
            st.dataframe(show, use_container_width=True, hide_index=True)

    st.subheader("유의사항")
    st.warning(
        "본 도구는 투자 판단의 보조 자료일 뿐, 매수·매도 권유가 아닙니다. "
        "투자 결과에 대한 책임은 전적으로 투자자 본인에게 있습니다.",
        icon=None,
    )
    st.markdown(
        """
        - 모델은 **과거 패턴**을 학습한 결과이므로, 시장 급변(거시 이벤트, 정책 변화, 단발성 뉴스)에 약합니다
        - **거래량·시가총액이 작은 ETF**는 신호의 신뢰도가 낮아질 수 있습니다
        - **합성·레버리지·선물·인버스 ETF**는 일반 가격 메커니즘과 다르므로 학습·예측 모두에서 제외됩니다
        - 학습은 **확률 ≥ 0.70**만 추천 대상으로 노출하며, 정밀도/재현율 트레이드오프는 모델 정보 탭에서 확인하세요
        - 학습 데이터에 없는 신규 ETF나 상장 직후 종목은 충분한 윈도우(100거래일)가 누적되어야 추천 대상에 포함됩니다
        """
    )

    st.divider()
    st.caption(
        "데이터 출처: [FinanceDataReader](https://github.com/FinanceData/FinanceDataReader)  ·  "
        "코드: [GitHub](https://github.com/0jjuni/etf-predictor)"
    )
