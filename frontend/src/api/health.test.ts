import { afterEach, expect, test, vi } from "vitest";

import { fetchHealth } from "./health";

afterEach(() => {
  vi.restoreAllMocks();
});

test("returns backend health information", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok", service: "The VC Brain API" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );

  await expect(fetchHealth()).resolves.toEqual({
    status: "ok",
    service: "The VC Brain API",
  });
});
