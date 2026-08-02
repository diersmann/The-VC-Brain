import { describe, expect, it } from "vitest";

import { ApiError, apiFailureCopy, apiFailureKind } from "./errors";

describe("API failure states", () => {
  it("distinguishes permission and server failures", () => {
    expect(apiFailureKind(new ApiError("forbidden", 403))).toBe("permission");
    expect(apiFailureKind(new ApiError("server error", 503))).toBe("server");
    expect(apiFailureCopy(new ApiError("server error", 503)).message).toMatch(/no investment conclusion/i);
  });

  it("classifies a network TypeError as offline", () => {
    expect(apiFailureKind(new TypeError("Failed to fetch"))).toBe("offline");
    expect(apiFailureCopy(new TypeError("Failed to fetch")).title).toBe("Connection unavailable");
  });
});
