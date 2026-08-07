export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly retryable?: boolean;
  readonly requestId?: string;
  readonly detail?: unknown;
  readonly errorVersion?: string;

  constructor(
    message: string,
    status: number,
    metadata?: {
      code?: string;
      retryable?: boolean;
      requestId?: string;
      detail?: unknown;
      version?: string;
    },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = metadata?.code;
    this.retryable = metadata?.retryable;
    this.requestId = metadata?.requestId;
    this.detail = metadata?.detail;
    this.errorVersion = metadata?.version;
  }
}

type ErrorEnvelope = {
  detail?: unknown;
  error?: {
    version?: unknown;
    code?: unknown;
    message?: unknown;
    retryable?: unknown;
    request_id?: unknown;
  };
};

function parseErrorEnvelope(payload: unknown): {
  message?: string;
  code?: string;
  retryable?: boolean;
  requestId?: string;
  detail?: unknown;
  version?: string;
} | null {
  if (payload === null || typeof payload !== "object") return null;
  const envelope = payload as ErrorEnvelope;
  const metadata = envelope.error;
  if (metadata === null || typeof metadata !== "object") {
    return "detail" in envelope ? { detail: envelope.detail } : null;
  }
  const message = typeof metadata.message === "string" ? metadata.message : undefined;
  const code = typeof metadata.code === "string" ? metadata.code : undefined;
  const retryable = typeof metadata.retryable === "boolean" ? metadata.retryable : undefined;
  const requestId = typeof metadata.request_id === "string" ? metadata.request_id : undefined;
  const version = typeof metadata.version === "string" ? metadata.version : undefined;
  if (!message && !code && retryable === undefined && !requestId && !version) {
    return "detail" in envelope ? { detail: envelope.detail } : null;
  }
  return { message, code, retryable, requestId, version, detail: envelope.detail };
}

/**
 * Convert a non-successful fetch response into the typed error consumed by
 * query/mutation UI states. A cloned response is read so the API's optional
 * v1 error metadata can be exposed without consuming the caller's body.
 * AbortErrors still propagate unchanged from fetch.
 */
export async function throwIfNotOk(response: Response, operation: string): Promise<void> {
  if (!response.ok) {
    let metadata: ReturnType<typeof parseErrorEnvelope> = null;
    try {
      metadata = parseErrorEnvelope(await response.clone().json());
    } catch {
      // Empty, malformed, and non-JSON legacy bodies retain the old message.
    }
    throw new ApiError(
      metadata?.message ?? `${operation} failed with status ${response.status}`,
      response.status,
      metadata
        ? {
            code: metadata.code,
            retryable: metadata.retryable,
            requestId: metadata.requestId,
            detail: metadata.detail,
            version: metadata.version,
          }
        : undefined,
    );
  }
}

export type ApiFailureKind = "not-found" | "permission" | "offline" | "server" | "request";

export function apiFailureKind(error: unknown): ApiFailureKind {
  if (error instanceof ApiError) {
    if (error.status === 404) return "not-found";
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
    case "not-found":
      return {
        title: "Record not found",
        message: "This investment record is no longer available. Return to the queue and choose another record.",
      };
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
