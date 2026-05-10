"""Generate today's blog post (MDX) using an LLM with structured templates.

Reads the latest run from Supabase, picks a post template based on the
day's data state, asks the configured LLM to write a Korean analysis, and
writes the result to web/content/posts/<target_date>.mdx.

Designed to run inside GitHub Actions cron right after `python -m ml.train`
finishes. The next git commit + push triggers a Vercel rebuild.

Templates are designed to keep voice and structure consistent across days
so the blog reads like a series, not random one-off posts.

Provider abstraction:
  - LLM_PROVIDER=gemini (default) — uses GEMINI_API_KEY, model gemini-2.5-flash
  - LLM_PROVIDER=anthropic       — uses ANTHROPIC_API_KEY, model claude-sonnet-4-6
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from textwrap import dedent

# Path bootstrap — same trick as backfill.py
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import (
    fetch_latest_model_metrics,
    fetch_predictions_for_latest_run,
    fetch_resolved_history,
)

log = logging.getLogger("etf.post")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

POSTS_DIR = ROOT / "web" / "content" / "posts"


# --------------------------------------------------------------------------- #
# Style guide — shared by every template.
# --------------------------------------------------------------------------- #

STYLE_GUIDE = dedent(
    """
    [공통 스타일 가이드 — 모든 포스트에 적용]

    너는 한국 ETF 시장 분석 블로그의 편집자다. 매일 발행되는 일일 분석을 쓴다.
    이 블로그는 정밀도 우선 설계의 AI 모델을 운영하며, 정직성과 일관성이 핵심이다.

    톤:
    - 정보 제공자 톤. 차분하고 분석적. 흥분/과장 금지.
    - "사세요", "추천합니다" 같은 명령형 절대 금지.
    - 대신 "관심 종목으로 검토할 만하다", "모델은 ~로 본다", "신호를 포착했다" 등
      정보 제공형 표현 사용.
    - 한국 투자자에게 익숙한 말투. 영어 용어는 한 번씩만 병기 (예: "정밀도(Precision)").

    구조:
    - 마크다운으로 작성. ## 서브섹션 사용 가능.
    - 본문만 작성. 제목과 frontmatter는 별도 처리되니 쓰지 마라.
    - 이모지 사용 금지.
    - 코드/표 사용 금지 (블로그 본문이라 시각적 요소 최소화).

    공통 마무리 라인:
    - 본문 마지막에 항상 다음 한 줄을 그대로 추가한다:
      "본 분석은 정보 제공 목적이며, 투자 판단의 책임은 본인에게 있습니다."
    """
).strip()


# --------------------------------------------------------------------------- #
# Templates — one per post type.
# --------------------------------------------------------------------------- #

TEMPLATE_DAILY_PICKS = dedent(
    """
    [오늘 포스트 유형: 정상 추천 종목 있는 날]

    구조:
    1. 시장 관전 포인트 — 오늘 시장 분위기와 모델이 어떤 신호를 잡았는지
       1~2문장으로 요약. 추상적 거시 발언 금지, 모델 결과에 근거.
    2. ## 오늘의 추천 — 추천 종목 각각에 대해 짧은 단락:
       - 종목명과 모델 확률
       - 모델이 잡은 핵심 신호 (모멘텀/RSI/거래량/시장 맥락 중 강조점 1~2개)
       - 제공된 관련 기사가 있으면 그 주제를 한 줄로 자연스럽게 언급
    3. ## 모델 코멘트 — 정밀도 우선 설계 관점에서 이 추천의 신뢰도. 1~2문장.
       전날 적중률 데이터가 있으면 그것도 짧게 인용 가능.
    4. 마무리 — 위에 명시한 공통 disclaimer 한 줄.

    분량: 본문 전체 450~700자 (공백 포함).
    """
).strip()

TEMPLATE_NO_PICKS_WITH_FALLBACK = dedent(
    """
    [오늘 포스트 유형: 정상 추천 0건, 참고용 fallback 후보 있는 날]

    이런 날도 정밀도 우선 설계의 자연스러운 결과다. 정직함의 신호로 다뤄라.

    구조:
    1. 시장 진단 — 모델이 70% 임계값을 넘는 종목을 못 찾은 이유에 대한 짧은 시장
       관전 (1~2문장).
    2. ## 참고 종목 — fallback 후보의 종목명, 확률, 한 줄 코멘트. 70% 미만이라
       추천이 아닌 정성 검토용임을 명확히.
    3. ## 정밀도 우선 시스템의 의미 — "추천 없음"인 날이 곧 노이즈를 거른 결과
       라는 점을 2~3문장으로 설명. 한 번도 똑같이 쓰지 말고 그날 데이터에 맞춰
       자연스럽게 풀어쓸 것.
    4. 마무리 — 공통 disclaimer 한 줄.

    분량: 본문 전체 350~550자.
    """
).strip()

TEMPLATE_NO_DATA = dedent(
    """
    [오늘 포스트 유형: 정상 추천 0건, fallback도 없음 (드문 케이스)]

    구조:
    1. 시장 진단 — 모델이 어떤 ETF에서도 의미 있는 신호를 잡지 못한 점을 솔직히
       기술. 정직성이 핵심.
    2. ## 모델은 무엇을 보고 있나 — 평소 어떤 시그널을 보는지 짧게 환기 (모멘텀/
       RSI/거래량/시장 맥락 중 그날 두드러진 부분). 일관된 메시지로.
    3. 마무리 — 공통 disclaimer 한 줄.

    분량: 본문 전체 250~450자.
    """
).strip()


# --------------------------------------------------------------------------- #
# Context builders — turn raw data into compact LLM input.
# --------------------------------------------------------------------------- #

def _format_news(articles: list[dict] | None, limit: int = 3) -> str:
    if not articles:
        return ""
    lines = []
    for a in articles[:limit]:
        src = a.get("source", "")
        title = a.get("title", "").strip()
        if title:
            lines.append(f"  - [{src}] {title}")
    return "\n".join(lines)


def _format_picks_block(picks: list[dict]) -> str:
    rows = []
    for p in picks:
        line = (
            f"- {p['name']} ({p['symbol']}): 확률 {p['probability'] * 100:.1f}%"
        )
        news = _format_news(p.get("news_json"))
        if news:
            line += "\n  관련 기사:\n" + news
        rows.append(line)
    return "\n".join(rows)


def _format_fallback_block(items: list[dict]) -> str:
    rows = []
    for p in items[:3]:
        rows.append(
            f"- {p['name']} ({p['symbol']}): 확률 {p['probability'] * 100:.1f}% "
            f"· 정밀도 {(p.get('precision_band') or 0) * 100:.1f}%"
        )
    return "\n".join(rows)


def _format_recent_record(history: list[dict], days: int = 5) -> str:
    """Last N days of resolved predictions with hit rate, used as evidence
    in the LLM prompt to ground self-evaluation lines."""
    if not history:
        return "(누적 검증 기록 없음)"
    recent = sorted(history, key=lambda r: r["target_date"], reverse=True)
    by_date: dict[str, list[dict]] = {}
    for row in recent:
        by_date.setdefault(row["target_date"], []).append(row)
    lines = []
    for d in sorted(by_date.keys(), reverse=True)[:days]:
        rows = by_date[d]
        hits = sum(1 for r in rows if r.get("outcome"))
        lines.append(
            f"- {d}: 추천 {len(rows)}건 / 적중 {hits}건"
        )
    return "\n".join(lines) if lines else "(최근 검증 기록 없음)"


def build_user_prompt(
    target_date: str,
    picks: list[dict],
    metrics: dict | None,
    history: list[dict],
    template: str,
) -> str:
    fallback = (metrics or {}).get("fallback_picks_json") or []
    parts = [
        STYLE_GUIDE,
        "",
        template,
        "",
        f"## 오늘의 학습 결과 ({target_date})",
        "",
    ]

    if picks:
        parts.append("### 정상 추천 종목 (확률 ≥ 70%)")
        parts.append(_format_picks_block(picks))
    else:
        parts.append("### 정상 추천 종목: 없음")

    if fallback:
        parts.append("")
        parts.append("### 참고용 후보 (fallback)")
        parts.append(_format_fallback_block(fallback))

    parts.append("")
    parts.append("### 최근 검증 기록 (최근 5거래일)")
    parts.append(_format_recent_record(history))

    parts.append("")
    parts.append(
        "위 데이터를 가지고 오늘의 일일 분석 본문을 작성해줘. "
        "본문만 출력하고, 제목이나 frontmatter는 따로 만들 필요 없다."
    )
    return "\n".join(parts)


def select_template(picks: list[dict], metrics: dict | None) -> str:
    if picks:
        return TEMPLATE_DAILY_PICKS
    fallback = (metrics or {}).get("fallback_picks_json") or []
    if fallback:
        return TEMPLATE_NO_PICKS_WITH_FALLBACK
    return TEMPLATE_NO_DATA


# --------------------------------------------------------------------------- #
# LLM providers
# --------------------------------------------------------------------------- #

def call_gemini(prompt: str) -> str:
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
    )
    resp = model.generate_content(prompt)
    return resp.text.strip()


def call_anthropic(prompt: str) -> str:
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if b.type == "text").strip()


def call_llm(prompt: str) -> str:
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    if provider == "anthropic":
        return call_anthropic(prompt)
    return call_gemini(prompt)


# --------------------------------------------------------------------------- #
# MDX writer
# --------------------------------------------------------------------------- #

def make_title(target_date: str, picks: list[dict], metrics: dict | None) -> str:
    if picks:
        primary = picks[0]
        if len(picks) == 1:
            return f"{target_date} ETF 추천: {primary['name']}"
        return f"{target_date} ETF 추천: {primary['name']} 외 {len(picks) - 1}건"
    fallback = (metrics or {}).get("fallback_picks_json") or []
    if fallback:
        return f"{target_date} 시장 분석: 추천 없음, 참고 후보 {fallback[0]['name']}"
    return f"{target_date} 시장 분석: 추천 없음"


def make_description(picks: list[dict], metrics: dict | None) -> str:
    if picks:
        names = ", ".join(p["name"] for p in picks[:3])
        return f"오늘의 모델 추천: {names}"
    fallback = (metrics or {}).get("fallback_picks_json") or []
    if fallback:
        return (
            f"추천 기준선(70%) 통과 종목 없음 — 참고 후보로 {fallback[0]['name']} "
            "등이 거론됩니다."
        )
    return "오늘은 모델이 의미 있는 신호를 찾지 못한 날입니다."


def write_post(
    target_date: str,
    body: str,
    picks: list[dict],
    metrics: dict | None,
) -> Path:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = POSTS_DIR / f"{target_date}.mdx"

    title = make_title(target_date, picks, metrics)
    description = make_description(picks, metrics)
    picks_yaml = ""
    if picks:
        picks_yaml = "picks:\n" + "\n".join(
            f'  - {{symbol: "{p["symbol"]}", name: "{p["name"]}", probability: {p["probability"]:.4f}}}'
            for p in picks
        )

    front_lines = [
        "---",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f'date: "{target_date}"',
        f"description: {json.dumps(description, ensure_ascii=False)}",
    ]
    if picks_yaml:
        front_lines.append(picks_yaml)
    front_lines.append("---")
    frontmatter = "\n".join(front_lines)

    content = f"{frontmatter}\n\n{body.strip()}\n"
    out_path.write_text(content, encoding="utf-8")
    log.info("Wrote %s (%d bytes)", out_path, len(content))
    return out_path


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def main() -> int:
    target_date, picks_rows = fetch_predictions_for_latest_run(limit=20)
    if target_date is None:
        log.error("No model_metrics yet — skipping post generation.")
        return 0

    metrics = fetch_latest_model_metrics()
    history = fetch_resolved_history(limit=200)

    template = select_template(picks_rows, metrics)
    log.info(
        "Generating post for %s (picks=%d, fallback=%d, history=%d)",
        target_date,
        len(picks_rows),
        len((metrics or {}).get("fallback_picks_json") or []),
        len(history),
    )

    prompt = build_user_prompt(target_date, picks_rows, metrics, history, template)
    body = call_llm(prompt)
    write_post(target_date, body, picks_rows, metrics)
    return 0


if __name__ == "__main__":
    sys.exit(main())
