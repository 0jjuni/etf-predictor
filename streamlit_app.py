"""Streamlit entry point for HuggingFace Spaces.

The app reads predictions written by the daily GH Actions training job
from Supabase. It does not retrain or run inference itself.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app.db import fetch_history_for, fetch_latest_predictions

st.set_page_config(
    page_title="한국 ETF 예측기",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)

st.title("한국 ETF 다음날 2.5% 상승 예측")
st.caption("매일 KST 08:00에 모델을 재학습하여 결과를 저장합니다.")


@st.cache_data(ttl=300)
def _latest() -> pd.DataFrame:
    return pd.DataFrame(fetch_latest_predictions(limit=200))


@st.cache_data(ttl=300)
def _history(symbol: str) -> pd.DataFrame:
    return pd.DataFrame(fetch_history_for(symbol, limit=60))


df = _latest()

if df.empty:
    st.warning("아직 저장된 예측이 없어요. 첫 학습 잡이 실행되면 표시됩니다.")
    st.stop()

target_date = df["target_date"].iloc[0]
st.subheader(f"기준일: {target_date}  ·  추천 종목 {len(df)}개")

display = df[["symbol", "name", "probability", "rise_threshold"]].copy()
display["probability"] = (display["probability"] * 100).round(2)
display["rise_threshold"] = ((display["rise_threshold"] - 1) * 100).round(2)
display.columns = ["종목코드", "종목명", "상승확률(%)", "기준상승률(%)"]
st.dataframe(display, use_container_width=True, hide_index=True)

st.divider()
st.subheader("종목별 추천 이력")
choice = st.selectbox(
    "종목 선택",
    options=df["symbol"].tolist(),
    format_func=lambda s: f"{s} {df.loc[df['symbol'] == s, 'name'].iloc[0]}",
)
hist = _history(choice)
if hist.empty:
    st.info("이력이 없어요.")
else:
    hist["probability"] = (hist["probability"] * 100).round(2)
    st.line_chart(hist.set_index("target_date")["probability"])
    st.dataframe(
        hist[["target_date", "probability"]].rename(
            columns={"target_date": "날짜", "probability": "확률(%)"}
        ),
        use_container_width=True,
        hide_index=True,
    )
