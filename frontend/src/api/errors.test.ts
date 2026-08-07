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

  it("preserves the response status when normalizing legacy failures", async () => {
    await expect(throwIfNotOk(new Response(null, { status: 409 }), "Saving thesis")).rejects.toThrow(
      "Saving thesis failed with status 409",
    );

    await expect(throwIfNotOk(new Response(null, { status: 403 }), "Feedback request")).rejects.toMatchObject({
      name: "ApiError",
      status: 403,
    });
  });

  it("parses optional v1 metadata without consuming the response contract", async () => {
    const response = new Response(
      JSON.stringify({
        version: "v1",
        detail: "Conflict detail retained for compatibility",
        error: {
          version: "v1",
          code: "conflict",
          message: "The request conflicts with the current resource state.",
          retryable: false,
          request_id: "request-123",
        },
      }),
      { status: 409, headers: { "Content-Type": "application/json" } },
    );

    await expect(throwIfNotOk(response, "Saving thesis")).rejects.toMatchObject({
      status: 409,
      message: "The request conflicts with the current resource state.",
      code: "conflict",
      retryable: false,
      requestId: "request-123",
      detail: "Conflict detail retained for compatibility",
      errorVersion: "v1",
    });
    await expect(response.json()).resolves.toMatchObject({ version: "v1" });
  });

  it("retains legacy detail bodies without treating them as metadata", async () => {
    await expect(
      throwIfNotOk(new Response(JSON.stringify({ detail: "legacy detail" }), { status: 422 }), "Validation request"),
    ).rejects.toMatchObject({
      status: 422,
      message: "Validation request failed with status 422",
      code: undefined,
      detail: "legacy detail",
    });
  });
});
