const WEEKDAY_KR = ["일", "월", "화", "수", "목", "금", "토"];

export function formatKoreanDate(target: string | null | undefined): string {
  if (!target) return "—";
  const d = new Date(target);
  if (Number.isNaN(d.getTime())) return target;
  return `${target} (${WEEKDAY_KR[d.getUTCDay()]})`;
}

export function pct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function signedPct(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const v = value * 100;
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(digits)}%`;
}
