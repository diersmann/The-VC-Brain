import { afterEach, expect, test, vi } from "vitest";

import { ApiError } from "./errors";
import { saveActiveThesis, type ThesisPayload } from "./theses";

afterEach(() => {
  vi.restoreAllMocks();
});

const payload: ThesisPayload = {
  name: "Climate software",
  stages: ["seed"],
  sectors: ["climate"],
  excluded_sectors: [],
  regions: ["Europe"],
  check_size_min_k_eur: 100,
  check_size_max_k_eur: 500,
  ownership_target_pct: 10,
  risk_appetite: "balanced",
  scoring_weights: {},
};

test("normalizes thesis save failures and preserves status", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 422 })));

  await expect(saveActiveThesis(payload)).rejects.toBeInstanceOf(ApiError);
  await expect(saveActiveThesis(payload)).rejects.toMatchObject({
    message: "Saving thesis failed with status 422",
    status: 422,
  });
});
