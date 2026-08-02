export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export type ApiFailureKind = "permission" | "offline" | "server" | "request";

export function apiFailureKind(error: unknown): ApiFailureKind {
  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 403) return "permission";
    if (error.status >= 500) return "server";
    return "request";
  }

  if (error instanceof TypeError || (typeof navigator !== "undefined" && !navigator.onLine)) {
    return "offline";
  }

  return "request";
}

export function apiFailureCopy(error: unknown): { title: string; message: string } {
  switch (apiFailureKind(error)) {
    case "permission":
      return {
        title: "Permission required",
        message: "Your workspace does not allow this data request. Ask an administrator for access.",
      };
    case "offline":
      return {
        title: "Connection unavailable",
        message: "The investment data service could not be reached. Check your connection and try again.",
      };
    case "server":
      return {
        title: "Investment data unavailable",
        message: "The investment data service returned an error. No investment conclusion was inferred from this failure.",
      };
    default:
      return {
        title: "Could not load investment data",
        message: "This request did not complete. No investment conclusion was inferred from this failure.",
      };
  }
}
