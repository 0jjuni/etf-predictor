"""Generate today's blog post (MDX) using an LLM.

Reads the latest run from Supabase, asks the configured LLM to write a brief
Korean analysis (200~500 words) referencing the picks and recent news, and
writes the result to web/content/posts/<target_date>.mdx.

Designed to run inside GitHub Actions cron right after `python -m ml.train`
has finished. The next git commit + push triggers a Vercel rebuild.

Provider abstraction:
  - LLM_PROVIDER=gemini (default) — uses GEMINI_API_KEY, model gemini-2.5-flash
  - LLM_PROVIDER=anthropic       — uses ANTHROPIC_API_KEY, model claude-sonnet-4-6

Required env vars in addition to the LLM key:
  SUPABASE_URL, SUPABASE_ANON_KEY (read-only is enough for this script)
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
)

log = logging.getLogger("etf.post")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

POSTS_DIR = ROOT / "web" / "content" / "posts"

SYSTEM_PROMPT = dedent(
    """
    너는 한국 ETF 시장 분석 블로그의 편집자다. 매일 모델이 생성한 추천 종목을
    바탕으로 친근하고 신뢰감 있는 한국어 일일 분석 포스트를 쓴다.

    포스트 작성 가이드:
    - 길이: 250~450자(공백 포함) 정도. 너무 길지 않게.
    - 톤: 정보 제공 위주, "사세요" 같은 명령형은 절대 금지. "모델은 ~로 본다",
      "관심 종목으로 검토해볼 만하다" 같은 정보 제공형 표현 사용.
    - 구조:
      1) 도입 한 줄 — 오늘 시장에서 모델이 어떻게 봤는지 요약
      2) 추천 종목 한두 개에 대한 짧은 코멘트 (특정 테마 / 모멘텀 / 최근 뉴스 키워드)
      3) 모델 한계 / 보조 자료임을 한 줄로 짚기
    - "정밀도 우선 설계" 라는 본 모델의 철학을 자연스럽게 녹일 것.
    - 마크다운 형식으로 작성 (제목은 frontmatter에서 처리, 본문은 본문만).
    - 코드 블록, 표 같은 무거운 요소는 사용하지 않는다.
    - 이모지는 사용하지 않는다.
    """
).strip()


def build_user_prompt(target_date: str, picks: list[dict], metrics: dict | None) -> str:
    pick_lines = (
        "\n".join(
            f"- {p['name']} ({p['symbol']}): 상승 확률 {p['probability'] * 100:.1f}%"
            + (
                "\n  관련 기사: "
                + "; ".join(
                    f"{a.get('source', '')} · {a.get('title', '')}"
                    for a in (p.get("news_json") or [])[:3]
                )
                if p.get("news_json")
                else ""
            )
            for p in picks
        )
        if picks
        else "(오늘은 정상 추천 기준선(70%)을 통과한 종목이 없음)"
    )

    fallback_lines = ""
    if not picks and metrics and metrics.get("fallback_picks_json"):
        fb = metrics["fallback_picks_json"]
        fallback_lines = "\n".join(
            f"- {p['name']} ({p['symbol']}): 확률 {p['probability'] * 100:.1f}% (참고용)"
            for p in fb[:3]
        )

    return dedent(
        f"""
        ## 오늘의 학습 결과 ({target_date})

        ### 정상 추천 종목
        {pick_lines}

        {"### 참고용 종목 (기준 미달)\n" + fallback_lines if fallback_lines else ""}

        위 데이터를 가지고 오늘의 일일 분석 본문을 작성해줘.
        본문만 출력하고, 제목이나 frontmatter는 따로 만들 필요 없다.
        """
    ).strip()


def call_gemini(system: str, user: str) -> str:
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        system_instruction=system,
    )
    resp = model.generate_content(user)
    return resp.text.strip()


def call_anthropic(system: str, user: str) -> str:
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        max_tokens=1500,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in msg.content if b.type == "text").strip()


def call_llm(system: str, user: str) -> str:
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    if provider == "anthropic":
        return call_anthropic(system, user)
    return call_gemini(system, user)


def make_title(target_date: str, picks: list[dict]) -> str:
    if picks:
        primary = picks[0]
        return f"{target_date} ETF 추천: {primary['name']} 외 {len(picks) - 1}건" if len(picks) > 1 else f"{target_date} ETF 추천: {primary['name']}"
    return f"{target_date} 시장 분석: 정상 추천 없음"


def make_description(picks: list[dict], metrics: dict | None) -> str:
    if picks:
        names = ", ".join(p["name"] for p in picks[:3])
        return f"오늘의 모델 추천: {names}"
    fb = (metrics or {}).get("fallback_picks_json") or []
    if fb:
        return f"오늘은 추천 기준선을 통과한 종목이 없어 참고용 후보({fb[0]['name']} 등)만 표시됩니다."
    return "오늘은 모델이 추천할 종목을 찾지 못했습니다."


def write_post(target_date: str, body: str, picks: list[dict], metrics: dict | None) -> Path:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = POSTS_DIR / f"{target_date}.mdx"

    title = make_title(target_date, picks)
    description = make_description(picks, metrics)
    picks_yaml = ""
    if picks:
        picks_yaml = "picks:\n" + "\n".join(
            f'  - {{symbol: "{p["symbol"]}", name: "{p["name"]}", probability: {p["probability"]:.4f}}}'
            for p in picks
        )

    frontmatter = dedent(
        f"""
        ---
        title: {json.dumps(title, ensure_ascii=False)}
        date: "{target_date}"
        description: {json.dumps(description, ensure_ascii=False)}
        {picks_yaml}
        ---
        """
    ).strip()

    content = f"{frontmatter}\n\n{body.strip()}\n"
    out_path.write_text(content, encoding="utf-8")
    log.info("Wrote %s (%d bytes)", out_path, len(content))
    return out_path


def main() -> int:
    target_date, picks_rows = fetch_predictions_for_latest_run(limit=20)
    if target_date is None:
        log.error("No model_metrics yet — skipping post generation.")
        return 0

    metrics = fetch_latest_model_metrics()
    log.info("Generating post for %s (picks=%d)", target_date, len(picks_rows))

    user_prompt = build_user_prompt(target_date, picks_rows, metrics)
    body = call_llm(SYSTEM_PROMPT, user_prompt)
    write_post(target_date, body, picks_rows, metrics)
    return 0


if __name__ == "__main__":
    sys.exit(main())
