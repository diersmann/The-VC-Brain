import { describe, expect, test } from "vitest";

import { displayScore, scorePercent, scoreVisual } from "./displayMetrics";

describe("display metrics", () => {
  test("normalizes ratio and percentage inputs consistently", () => {
    expect(scorePercent(0.76)).toBe(76);
    expect(scorePercent(76)).toBe(76);
    expect(scorePercent(-0.2)).toBe(0);
    expect(scorePercent(140)).toBe(100);
    expect(scorePercent(Number.NaN)).toBeNull();
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
});
