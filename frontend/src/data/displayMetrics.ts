export type ScoreVisual = {
  percent: number | null;
  status: string;
  color: string;
  soft: string;
};

export type ScoreVisualMode = "profile" | "decision";

export function scorePercent(value: number | null | undefined): number | null {
  if (value == null || Number.isNaN(value)) return null;
  return clampPercent(value <= 1 ? value * 100 : value);
}

export function displayScore(value: number | null | undefined, alreadyPercent = false): string {
  const percent = value == null || Number.isNaN(value)
    ? null
    : clampPercent(alreadyPercent ? value : value <= 1 ? value * 100 : value);
  return percent == null ? "Not scored" : `${percent}%`;
}

export function scoreVisual(value: number | null | undefined, mode: ScoreVisualMode = "profile"): ScoreVisual {
  const percent = scorePercent(value);
  if (percent == null) return { percent: null, status: "No score", color: "#9aa8ba", soft: "#edf1f5" };

  if (mode === "decision") {
    if (percent >= 75) return { percent, status: "Strong", color: "#2f8b72", soft: "#e4f2ed" };
    if (percent >= 55) return { percent, status: "Watch", color: "#557dc0", soft: "#e7eef9" };
    if (percent >= 40) return { percent, status: "Investigate", color: "#b87932", soft: "#fff1df" };
    return { percent, status: "Risk", color: "#b9575f", soft: "#fbe8e9" };
  }

  if (percent >= 70) return { percent, status: "Strong", color: "#2f8b72", soft: "#e4f2ed" };
  if (percent >= 45) return { percent, status: "Watch", color: "#c6893f", soft: "#fff1df" };
  return { percent, status: "Risk", color: "#c35f65", soft: "#fbe8e9" };
}

function clampPercent(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}
