import { afterEach, expect, test, vi } from "vitest";

import { ApiError } from "./errors";
import { submitPitch } from "./inbound";

afterEach(() => {
  vi.restoreAllMocks();
});

test("normalizes pitch submission failures and preserves status", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 413 })));

  await expect(submitPitch(new FormData(), undefined, "pitch-key")).rejects.toBeInstanceOf(ApiError);
  await expect(submitPitch(new FormData())).rejects.toMatchObject({ status: 413 });
});
