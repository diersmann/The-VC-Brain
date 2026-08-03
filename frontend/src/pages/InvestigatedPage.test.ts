import { describe, expect, test } from "vitest";

import { displayScore } from "../data/portfolioMetrics";

describe("Investigated score display", () => {
  test("keeps missing scores distinct from measured zero", () => {
    expect(displayScore(null)).toBe("Not scored");
    expect(displayScore(0)).toBe("0%");
    expect(displayScore(0, true)).toBe("0%");
  });
});
