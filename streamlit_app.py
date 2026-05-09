"""Streamlit entry point for HuggingFace Spaces.

Reads predictions, the holdout precision curve, and resolved-outcome history
from Supabase. No retraining or live inference happens here.
"""
from __future__ import annotations

import bisect
from datetime import datetime

import pandas as pd
import streamlit as st

from app.db import (
    fetch_history_for,
    fetch_latest_model_metrics,
    fetch_predictions_for_latest_run,
    fetch_resolved_history,
)

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


def _format_korean_date(target_date: str | None) -> str:
    if not target_date:
        return "—"
    ts = pd.Timestamp(target_date)
    return f"{ts.date()} ({WEEKDAY_KR[ts.dayofweek]})"


st.set_page_config(
    page_title="ETF 종가 예측기",
    page_icon=":chart_with_upwards_trend:",
    layout="centered",
)

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
      .big-date { font-size: 1.05rem; font-weight: 600; color: #0f172a; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("ETF 종가 예측기")
st.markdown(
    "<div class='small-caption'>"
    "한국 ETF 중에서 <b>다음 거래일 종가</b>가 직전 거래일 종가 대비 "
    "<b>+2.5% 이상</b> 오를 가능성이 높은 종목을 매일 추천합니다. "
    "매일 KST 08:00에 모델이 자동으로 다시 학습됩니다."
    "</div>",
    unsafe_allow_html=True,
)
st.write("")


# --------------------------------------------------------------------------- #
# Data loaders
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=300)
def _latest_run() -> tuple[str | None, pd.DataFrame]:
    target_date, rows = fetch_predictions_for_latest_run(limit=200)
    return target_date, pd.DataFrame(rows)


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


target_date, preds_df = _latest_run()
metrics = _latest_metrics()
hist_df = _resolved_history()

tab_picks, tab_history, tab_model = st.tabs(["추천 종목", "검증 기록", "모델 정보"])

# --------------------------------------------------------------------------- #
# Tab 1 — Today's picks
# --------------------------------------------------------------------------- #
with tab_picks:
    if target_date is None:
        st.info(
            "아직 학습이 한 번도 실행되지 않았습니다. 매일 KST 08:00에 자동으로 학습됩니다."
        )
    else:
        date_label = _format_korean_date(target_date)
        st.markdown(
            f"<div class='big-date'>예측 대상일 · {date_label}</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "이 날짜에 적용되는 추천입니다. "
            "모델은 직전 거래일 종가를 기준으로 다음 거래일 종가가 +2.5% 이상 오를 확률을 계산했어요."
        )

        if preds_df.empty:
            st.warning(
                f"**{date_label}에는 추천할 종목이 없습니다.**  \n"
                "모델은 모든 한국 ETF에 대해 상승 확률을 계산했지만, "
                "이번에는 추천 기준선(70%)을 넘는 종목이 없었어요. "
                "시장이 잠잠하거나 뚜렷한 모멘텀 신호가 없는 날이라는 뜻입니다."
            )
        else:
            st.markdown(f"**{len(preds_df)}개 종목 추천**")
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
                            help="모델이 추정한 +2.5% 상승 확률",
                            format="%.1f%%",
                            min_value=0,
                            max_value=100,
                        ),
                        "예상정밀도": st.column_config.NumberColumn(
                            help="이 확률 구간 종목들이 테스트셋에서 실제로 +2.5% 상승한 비율",
                            format="%.1f%%",
                        ),
                    },
                )
            else:
                view.columns = ["코드", "종목명", "상승확률"]
                st.dataframe(view, use_container_width=True, hide_index=True)

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
        st.info(
            "검증된 예측 이력이 아직 없어요. 매일 학습이 며칠 누적되거나 백필을 한 번 돌리면 채워집니다."
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
# Tab 3 — Model card (friendly first, technical details below)
# --------------------------------------------------------------------------- #
with tab_model:
    st.subheader("한 줄 요약")
    st.info(
        "한국 ETF 중에서 **다음 거래일에 +2.5% 이상 오를 가능성이 높은 종목**을 "
        "매일 자동으로 골라줍니다."
    )

    st.subheader("모델은 무엇을 보나요?")
    st.markdown(
        """
        **최근 100거래일(약 5개월) 동안의 가격 흐름**을 다음 세 가지 관점에서 분석합니다:

        - **가격이 매일 얼마나 움직였는지** — 오르내림의 패턴을 봅니다
          *(기술명: 일간 변동률 / Change)*
        - **시장이 과열되었는지, 식었는지** — 가격이 너무 빨리 올랐다면 곧 조정이 올 수 있고, 너무 떨어졌다면 반등 여지가 있어요
          *(기술명: RSI(14) — 0~100 사이 값, 70+면 과매수, 30 미만이면 과매도)*
        - **추세가 강해지고 있는지, 약해지고 있는지** — 10거래일 전 대비 가격 변화로 모멘텀을 측정해요
          *(기술명: 모멘텀(10))*

        이 세 가지를 종합해 ETF별로 **0~100% 사이의 상승 확률**을 매기고, **70% 이상**인 종목만 추천 표에 보여줍니다.
        """
    )

    st.subheader("어떻게 학습하나요?")
    st.markdown(
        """
        - **매일 새벽**(KST 08:00)에 한국 ETF 전체의 최신 데이터를 다시 받아서 모델을 처음부터 다시 학습합니다
        - 학습 데이터의 **80%로 학습**하고 **20%는 검증용**으로 떼어 두어, 모델이 얼마나 정확한지 매일 측정합니다
        - **합성·레버리지·선물·인버스 ETF는 제외** — 일반 ETF와 가격 메커니즘이 달라서 모델이 잘못 배울 수 있어요
        """
    )

    st.subheader("왜 정밀도(Precision)에 집중하나요?")
    st.markdown(
        """
        실제 투자에 쓸 수 있는 자금은 한정적입니다. 그래서 이 모델은
        **\"많이 맞히는 것\"보다 \"맞힌다고 한 것을 정확히 맞히는 것\"** 을 우선합니다.

        - 100개 종목을 추천해서 30개가 맞히는 것보다,
          5개를 추천해서 4개가 맞히는 게 실제 수익에 더 도움이 됩니다
        - 그래서 추천 기준선을 **상승 확률 70% 이상**이라는 높은 값으로 설정했습니다
        - 결과적으로 **재현율(놓친 상승 종목 수)은 높아지지만**,
          **추천된 종목 하나하나의 적중률은 더 신뢰할만한 수준**이 돼요
        - "오늘 추천 없음"인 날도 정상입니다 — 신뢰도 낮은 신호를 억지로 만들지 않는다는 뜻입니다

        > 임계값 곡선에서 T를 0.5에서 0.7, 0.8, 0.9로 올릴수록
        > 정밀도가 가파르게 상승하는 걸 직접 확인할 수 있습니다.
        """
    )

    if metrics is None:
        st.info("학습이 한 번 이상 완료되어야 메트릭이 표시됩니다.")
    else:
        st.subheader("최근 학습 결과")
        c1, c2, c3 = st.columns(3)
        c1.metric("학습일", _format_korean_date(metrics["target_date"]))
        c2.metric("검증 샘플", f"{metrics['test_size']:,}")
        c3.metric("실제 상승 비율", f"{metrics['positive_rate'] * 100:.2f}%")
        st.caption(
            "검증 샘플 중 실제로 +2.5% 상승한 비율이 약 4%로 매우 적습니다. "
            "그래서 모델은 '확률 70% 이상'이라는 **높은 기준**을 적용해서 "
            "정확도를 우선시합니다."
        )

        st.subheader("기준선을 올리면 정확도가 어떻게 바뀌나요?")
        st.markdown(
            "<div class='small-caption'>"
            "<b>임계값(Threshold)</b>을 높이면 추천에 포함되는 종목 수는 줄지만, "
            "남은 종목들의 정확도는 일반적으로 더 높아집니다. "
            "즉 \"확률이 80%인 종목만 추천\"이 \"확률이 70%인 종목까지 추천\"보다 "
            "실제 적중률이 높습니다."
            "</div>",
            unsafe_allow_html=True,
        )
        df = _curve_df(metrics["metrics_json"])
        st.line_chart(
            df.set_index("threshold")[["precision", "recall", "f1"]],
            height=280,
            use_container_width=True,
        )

        with st.expander("임계값별 표 보기 (자세한 수치)"):
            show = df.copy()
            show["threshold"] = show["threshold"].map(lambda v: f"{v:.2f}")
            for col in ("precision", "recall", "f1"):
                show[col] = (show[col] * 100).round(2)
            show.columns = ["임계값", "정밀도(%)", "재현율(%)", "F1(%)", "후보수", "양성수"]
            st.dataframe(show, use_container_width=True, hide_index=True)
            st.caption(
                "정밀도 = 추천한 종목 중 실제 +2.5% 오른 비율  ·  "
                "재현율 = 실제 +2.5% 오른 종목 중 모델이 잡아낸 비율  ·  "
                "F1 = 둘의 조화평균  ·  "
                "후보수 = 임계값 이상으로 분류된 검증 샘플 수"
            )

    st.subheader("이용 시 유의사항")
    st.warning(
        "이 도구는 **투자 판단의 보조 자료**일 뿐이며, 매수·매도 권유가 아닙니다. "
        "투자 결과에 대한 책임은 전적으로 투자자 본인에게 있습니다."
    )
    st.markdown(
        """
        - **과거 패턴 기반 모델**입니다. 시장 급변(거시 이벤트, 정책 변화, 단발성 뉴스)에는 약합니다
        - **거래량과 시가총액이 작은 ETF**는 가격 변동의 무작위성이 크기 때문에 신호의 신뢰도가 떨어질 수 있어요
        - **합성·레버리지·선물·인버스 ETF**는 제외됩니다 — 일반 가격 메커니즘과 다르게 움직이기 때문
        - 신규 상장 ETF는 **100거래일 데이터가 누적**된 후에야 추천 후보가 됩니다
        - "추천 종목 없음"인 날은 **시스템 오류가 아니라** 모델이 충분히 신뢰할만한 신호를 찾지 못했다는 의미입니다
        """
    )

    with st.expander("자세한 기술 설명 (전문가용)"):
        st.markdown(
            """
            **모델**: XGBoost 이진 분류기 (Gradient Boosted Trees, `tree_method=hist`,
            `n_estimators=300`, `max_depth=6`, `learning_rate=0.05`)

            **입력 텐서**: 한 ETF당 `(window=100, features=3) → 300-dim flat vector`.
            Features는 일별 `Change`, `RSI(14)`, `Momentum(10)`. NaN drop 후 sliding window.

            **레이블**: `close[t] > 1.025 × close[t-1]` (다음날 종가 ≥ 2.5% 상승) — 클래스 불균형
            큼(양성률 ~4%).

            **검증**: stratified 80/20 split → holdout. 임계값 `[0.50, 0.55, ..., 0.95]`에서
            cumulative precision/recall/f1을 계산해 model_metrics에 JSONB로 저장.

            **추천 대상**: `predict_proba(today)[:, 1] >= 0.70` 인 ETF. 합성·레버리지·선물·인버스
            제외 (정규식 필터: `합성|레버리지|선물|인버스`).

            **학습 주기**: GitHub Actions cron `0 23 * * *` (UTC) = KST 08:00. CPU 기반 학습
            (GH Actions runner GPU 미지원). 학습마다 전체 ETF 데이터를 FDR로 재수집.

            **백필**: `scripts/backfill.py`로 walk-forward — 각 날짜 D에 대해 D 이전 데이터로만
            재학습 후 D 예측 + 실제 종가로 outcome 자동 fill. 누설 없음.
            """
        )

    st.divider()
    st.caption(
        f"최종 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}  ·  "
        "데이터 출처: [FinanceDataReader](https://github.com/FinanceData/FinanceDataReader)  ·  "
        "코드: [GitHub](https://github.com/0jjuni/etf-predictor)"
    )
