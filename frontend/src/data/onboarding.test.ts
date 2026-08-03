import { describe, expect, test } from "vitest";

import { checkBand, checkRange, checks, labelsFor, stages, toggleValue } from "./onboarding";

describe("onboarding thesis helpers", () => {
  test("round-trips supported check-size bands", () => {
    expect(checkRange("250-500")).toEqual([250, 500]);
    expect(checkBand(1000, null)).toBe("1000+");
    expect(checkBand(250, 500)).toBe("250-500");
  });

  test("toggles selections and renders known labels", () => {
    expect(toggleValue(["seed"], "pre-seed")).toEqual(["seed", "pre-seed"]);
    expect(toggleValue(["seed", "pre-seed"], "seed")).toEqual(["pre-seed"]);
    expect(labelsFor(stages, ["pre-seed", "seed"])).toBe("Pre-seed, Seed");
    expect(checks).toHaveLength(4);
  });
});
