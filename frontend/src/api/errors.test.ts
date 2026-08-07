import { describe, expect, it } from "vitest";

import { ApiError, apiFailureCopy, apiFailureKind, throwIfNotOk } from "./errors";

describe("API failure states", () => {
  it("distinguishes permission and server failures", () => {
    expect(apiFailureKind(new ApiError("missing", 404))).toBe("not-found");
    expect(apiFailureCopy(new ApiError("missing", 404)).title).toBe("Record not found");
    expect(apiFailureKind(new ApiError("forbidden", 403))).toBe("permission");
    expect(apiFailureKind(new ApiError("server error", 503))).toBe("server");
    expect(apiFailureCopy(new ApiError("server error", 503)).message).toMatch(/no investment conclusion/i);
  });

  it("classifies a network TypeError as offline", () => {
    expect(apiFailureKind(new TypeError("Failed to fetch"))).toBe("offline");
    expect(apiFailureCopy(new TypeError("Failed to fetch")).title).toBe("Connection unavailable");
  });

  it("preserves the response status when normalizing API failures", () => {
    expect(() => throwIfNotOk(new Response(null, { status: 409 }), "Saving thesis")).toThrow(
      "Saving thesis failed with status 409",
    );

    try {
      throwIfNotOk(new Response(null, { status: 403 }), "Feedback request");
      throw new Error("expected throw");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).status).toBe(403);
    }
  });
});
