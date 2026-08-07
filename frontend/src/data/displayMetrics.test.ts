import { describe, expect, test } from "vitest";

import { claimStatusViewModel, confidenceViewModel, displayScore, readinessViewModel, recommendationViewModel, ratingViewModel, scorePercent, scoreViewModel, scoreVisual, statusLabel, trendViewModel } from "./displayMetrics";

describe("display metrics", () => {
  test("normalizes ratio and percentage inputs consistently", () => {
    expect(scorePercent(0.76)).toBe(76);
    expect(scorePercent(76)).toBe(76);
    expect(scorePercent(-0.2)).toBe(0);
    expect(scorePercent(140)).toBe(100);
    expect(scorePercent(Number.NaN)).toBeNull();
    expect(scorePercent(Number.POSITIVE_INFINITY)).toBeNull();
    expect(displayScore(Number.NEGATIVE_INFINITY)).toBe("Not scored");
  });

  test("keeps missing scores distinct from measured zero", () => {
    expect(displayScore(null)).toBe("Not scored");
    expect(displayScore(0)).toBe("0%");
    expect(displayScore(76, true)).toBe("76%");
  });

  test("keeps profile and decision visual thresholds explicit", () => {
    expect(scoreVisual(0.7)).toMatchObject({ percent: 70, status: "Strong" });
    expect(scoreVisual(0.7, "decision")).toMatchObject({ percent: 70, status: "Watch" });
    expect(scoreVisual(null)).toMatchObject({ percent: null, status: "No score" });
  });

  test("provides typed score explanations without changing score bands", () => {
    expect(scoreViewModel(null)).toMatchObject({ label: "Not scored", status: "No score" });
    expect(scoreViewModel(0, "decision")).toMatchObject({ label: "0%", status: "Risk" });
    expect(scoreViewModel(0.8, "decision").explanation).toContain("strong band");
  });

  test("normalizes canonical trend states and explains missing comparisons", () => {
    expect(trendViewModel("improving")).toMatchObject({ state: "Improving", direction: "up" });
    expect(trendViewModel("unknown")).toMatchObject({ state: "Pending", label: "Trend pending", direction: "pending" });
    expect(trendViewModel(null).explanation).toContain("comparable prior assessment");
  });

  test("keeps confidence missing distinct from measured zero", () => {
    expect(confidenceViewModel(null)).toMatchObject({ percent: null, label: "Not scored", measured: false });
    expect(confidenceViewModel(0)).toMatchObject({ percent: 0, label: "0%", measured: true });
    expect(confidenceViewModel(null).explanation).toContain("unavailable");
    expect(statusLabel("tavily_synthesized")).toBe("Tavily Synthesized");
  });

  test("keeps canonical recommendation, readiness, rating, and claim labels", () => {
    expect(recommendationViewModel("Proceed")).toMatchObject({ label: "Move forward", detail: "Recommendation: Proceed" });
    expect(readinessViewModel("evidence-gap")).toMatchObject({ label: "Evidence gap" });
    expect(ratingViewModel("bullish")).toMatchObject({ label: "Bullish" });
    expect(claimStatusViewModel("tavily_synthesized")).toMatchObject({ label: "Synthesized" });
    expect(claimStatusViewModel(null)).toMatchObject({ label: "Unverified" });
  });
});
