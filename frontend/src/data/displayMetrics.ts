export type ScoreStatus = "Strong" | "Watch" | "Investigate" | "Risk" | "No score";

export type ScoreVisual = {
  percent: number | null;
  status: ScoreStatus;
  color: string;
  soft: string;
};

export type ScoreVisualMode = "profile" | "decision";

export type TrendState = "Improving" | "Stable" | "Declining" | "Pending";

export type TrendViewModel = {
  state: TrendState;
  label: string;
  explanation: string;
  direction: "up" | "flat" | "down" | "pending";
};

export type ConfidenceViewModel = {
  percent: number | null;
  label: string;
  explanation: string;
  measured: boolean;
};

export type ScoreViewModel = ScoreVisual & {
  label: string;
  explanation: string;
};

export type StatusViewModel = {
  label: string;
  detail: string;
  explanation: string;
  color: string;
  soft: string;
};

export type RecommendationStatus = "Proceed" | "Hold" | "Investigate";
export type ReadinessStatus = "ready" | "investigate" | "evidence-gap";
export type ClaimDisplayStatus = "Supported" | "Contradicted" | "Unverified" | "Synthesized" | "Observed";
export type RatingState = "Bullish" | "Neutral" | "Bearish" | "Pending";

export function scorePercent(value: number | null | undefined): number | null {
  if (value == null || !Number.isFinite(value)) return null;
  return clampPercent(value <= 1 ? value * 100 : value);
}

export function displayScore(value: number | null | undefined, alreadyPercent = false): string {
  const percent = value == null || !Number.isFinite(value)
    ? null
    : clampPercent(alreadyPercent ? value : value <= 1 ? value * 100 : value);
  return percent == null ? "Not scored" : `${percent}%`;
}

export function scoreViewModel(value: number | null | undefined, mode: ScoreVisualMode = "profile"): ScoreViewModel {
  const visual = scoreVisual(value, mode);
  return {
    ...visual,
    label: visual.percent == null ? "Not scored" : `${visual.percent}%`,
    explanation: scoreExplanation(visual.status, mode),
  };
}

export function trendViewModel(value: string | null | undefined): TrendViewModel {
  const normalized = normalizeTrend(value);
  if (normalized === "Improving") return { state: normalized, label: normalized, explanation: "Latest signal is improving versus the prior recorded assessment.", direction: "up" };
  if (normalized === "Declining") return { state: normalized, label: normalized, explanation: "Latest signal is declining versus the prior recorded assessment.", direction: "down" };
  if (normalized === "Stable") return { state: normalized, label: normalized, explanation: "No directional change is recorded versus the prior assessment.", direction: "flat" };
  return { state: normalized, label: "Trend pending", explanation: "Trend is unavailable until a comparable prior assessment is recorded.", direction: "pending" };
}

export function confidenceViewModel(value: number | null | undefined, subject = "Evidence"): ConfidenceViewModel {
  const percent = scorePercent(value);
  return {
    percent,
    label: percent == null ? "Not scored" : `${percent}%`,
    explanation: percent == null
      ? `${subject} confidence is unavailable until supporting evidence is recorded.`
      : `${subject} confidence reflects the available supporting evidence; missing evidence remains unknown.`,
    measured: percent != null,
  };
}

export function statusLabel(value: string | null | undefined, fallback = "Not set"): string {
  if (!value) return fallback;
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function recommendationViewModel(state: RecommendationStatus): StatusViewModel {
  if (state === "Proceed") return { label: "Move forward", detail: "Recommendation: Proceed", explanation: "Recorded evidence supports moving this opportunity forward for human review.", color: "#347c67", soft: "#e4f2ed" };
  if (state === "Hold") return { label: "Pause & verify", detail: "Recommendation: Hold", explanation: "Pause the opportunity while the listed risks or evidence gaps are verified.", color: "#a96e2d", soft: "#fff1df" };
  return { label: "Diligence needed", detail: "Recommendation: Investigate", explanation: "Additional diligence is required before a proceed or hold decision is supported.", color: "#5074a8", soft: "#e7eef9" };
}

export function readinessViewModel(state: ReadinessStatus): StatusViewModel {
  if (state === "ready") return { label: "Ready for review", detail: "Thesis and evidence cleared", explanation: "The existing thesis-alignment and evidence-confidence gates are cleared.", color: "#2f8b72", soft: "#e4f2ed" };
  if (state === "investigate") return { label: "Investigate", detail: "Human scrutiny required", explanation: "A decision signal exists, but human scrutiny is still required.", color: "#557dc0", soft: "#e7eef9" };
  return { label: "Evidence gap", detail: "Collect decision-critical proof", explanation: "Decision-critical evidence is missing; this is not a negative founder-quality score.", color: "#b87932", soft: "#fff1df" };
}

export function claimStatusViewModel(status: string | null | undefined): StatusViewModel {
  const normalized = status?.toLowerCase();
  if (normalized === "supported") return { label: "Supported", detail: "Supported evidence", explanation: "The claim is supported by reconciled evidence.", color: "#347c67", soft: "#e4f2ed" };
  if (normalized === "contradicted") return { label: "Contradicted", detail: "Conflicting evidence", explanation: "Available evidence conflicts with this claim.", color: "#b65d5d", soft: "#fbe8e9" };
  if (normalized === "tavily_synthesized" || normalized === "synthesized") return { label: "Synthesized", detail: "Source synthesis", explanation: "This claim is synthesized from source material and should be verified.", color: "#7656a5", soft: "#eee8f8" };
  if (normalized === "observed") return { label: "Observed", detail: "Direct observation", explanation: "This value is a direct source observation, not a quality conclusion.", color: "#5074a8", soft: "#e7eef9" };
  return { label: "Unverified", detail: "Verification needed", explanation: "The claim has not yet been sufficiently verified.", color: "#a96e2d", soft: "#fff1df" };
}

export function ratingViewModel(rating: string | null | undefined): StatusViewModel {
  const normalized = rating?.toLowerCase();
  if (normalized === "bullish") return { label: "Bullish", detail: "Positive assessment", explanation: "The recorded assessment is positive on this axis.", color: "#347c67", soft: "#e4f2ed" };
  if (normalized === "bearish") return { label: "Bearish", detail: "Negative assessment", explanation: "The recorded assessment is negative on this axis.", color: "#b65d5d", soft: "#fbe8e9" };
  if (normalized === "pending") return { label: "Pending", detail: "Assessment pending", explanation: "No assessment rating has been recorded for this axis yet.", color: "#7d8999", soft: "#edf1f5" };
  return { label: "Neutral", detail: "Neutral assessment", explanation: "The recorded assessment is neutral on this axis.", color: "#a96e2d", soft: "#fff1df" };
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

function normalizeTrend(value: string | null | undefined): TrendState {
  if (!value) return "Pending";
  const normalized = value.toLowerCase();
  if (normalized === "improving") return "Improving";
  if (normalized === "declining") return "Declining";
  if (normalized === "stable") return "Stable";
  return "Pending";
}

function scoreExplanation(status: ScoreStatus, mode: ScoreVisualMode): string {
  if (status === "No score") return "No score is recorded yet; this is distinct from a measured zero.";
  if (status === "Strong") return mode === "decision" ? "Recorded decision signal is in the strong band." : "Recorded profile signal is in the strong band.";
  if (status === "Watch") return mode === "decision" ? "Recorded decision signal needs review." : "Recorded profile signal needs review.";
  if (status === "Investigate") return "Recorded signal needs focused investigation.";
  return "Recorded signal is in the risk band and needs verification.";
}
