import { ImageResponse } from "next/og";
import {
  fetchLatestModelMetrics,
  fetchLatestPicks,
  fetchResolvedHistory,
} from "@/lib/queries";

export const alt = "ETF 종가 예측기";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Re-render daily so the OG image shows current state.
export const revalidate = 3600;

export default async function OpengraphImage() {
  const [{ targetDate, picks }, metrics, history] = await Promise.all([
    fetchLatestPicks(),
    fetchLatestModelMetrics(),
    fetchResolvedHistory(2000),
  ]);

  const fallback = metrics?.fallback_picks_json ?? [];
  const totalResolved = history.length;
  const totalHits = history.filter((h) => h.outcome === true).length;
  const empPrec = totalResolved > 0 ? (totalHits / totalResolved) * 100 : null;

  // Pick the headline ETF for the image: top regular pick, else top fallback.
  const headline =
    picks[0] ?? (fallback.length > 0 ? fallback[0] : null);

  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          padding: 64,
          backgroundImage:
            "linear-gradient(135deg, #4f46e5 0%, #6d28d9 50%, #7c3aed 100%)",
          color: "white",
          fontFamily: "sans-serif",
          position: "relative",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            fontSize: 18,
            fontWeight: 700,
            letterSpacing: 4,
            color: "rgba(255,255,255,0.85)",
            textTransform: "uppercase",
          }}
        >
          KOREAN ETF · DAILY SIGNAL
        </div>

        <div
          style={{
            display: "flex",
            marginTop: 28,
            fontSize: 64,
            fontWeight: 800,
            lineHeight: 1.15,
            letterSpacing: -1.5,
            maxWidth: 940,
          }}
        >
          ETF 종가 예측기
        </div>

        <div
          style={{
            display: "flex",
            marginTop: 12,
            fontSize: 28,
            fontWeight: 500,
            lineHeight: 1.4,
            color: "rgba(255,255,255,0.9)",
            maxWidth: 940,
          }}
        >
          내일 종가 +2.5% 오를 한국 ETF, AI가 매일 골라드립니다
        </div>

        {headline && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              marginTop: 40,
              padding: 24,
              borderRadius: 18,
              background: "rgba(255,255,255,0.12)",
              backdropFilter: "blur(8px)",
              maxWidth: 720,
            }}
          >
            <div
              style={{
                display: "flex",
                fontSize: 14,
                color: "rgba(255,255,255,0.75)",
                fontWeight: 600,
                letterSpacing: 2,
                textTransform: "uppercase",
              }}
            >
              {picks.length > 0 ? "오늘의 1순위" : "참고 후보"}
            </div>
            <div
              style={{
                display: "flex",
                marginTop: 8,
                fontSize: 36,
                fontWeight: 700,
              }}
            >
              {headline.name}
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: 16,
                marginTop: 8,
              }}
            >
              <span style={{ fontSize: 56, fontWeight: 800 }}>
                {(headline.probability * 100).toFixed(1)}%
              </span>
              <span style={{ fontSize: 18, color: "rgba(255,255,255,0.7)" }}>
                상승 확률
              </span>
            </div>
          </div>
        )}

        <div
          style={{
            display: "flex",
            gap: 28,
            marginTop: "auto",
            paddingTop: 24,
            color: "rgba(255,255,255,0.85)",
            fontSize: 16,
          }}
        >
          {targetDate && (
            <span>
              <strong style={{ color: "white" }}>{targetDate}</strong> 기준
            </span>
          )}
          <span>
            누적 검증{" "}
            <strong style={{ color: "white" }}>{totalResolved}</strong>건
          </span>
          {empPrec != null && (
            <span>
              경험적 정밀도{" "}
              <strong style={{ color: "white" }}>{empPrec.toFixed(1)}%</strong>
            </span>
          )}
        </div>
      </div>
    ),
    { ...size },
  );
}
