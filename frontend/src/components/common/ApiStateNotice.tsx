import { AlertTriangle, LoaderCircle, RefreshCw } from "lucide-react";
import { apiFailureCopy } from "../../api/errors";

export function ApiStateNotice({
  error,
  onRetry,
  loading = false,
  label = "investment data",
}: {
  error?: unknown;
  onRetry?: () => void;
  loading?: boolean;
  label?: string;
}) {
  if (loading) {
    return (
      <div role="status" className="flex items-center gap-2 rounded-md border border-accent/15 bg-accent-soft/40 px-4 py-3 text-sm text-ink-2">
        <LoaderCircle className="h-4 w-4 animate-spin text-accent" aria-hidden="true" />
        Loading {label}…
      </div>
    );
  }

  const copy = apiFailureCopy(error);
  return (
    <div role="alert" className="flex flex-wrap items-center justify-between gap-4 rounded-md border border-warn/25 bg-[#fff8ed] px-4 py-3 text-sm text-[#8d5e2b]">
      <div className="flex min-w-0 items-start gap-2.5">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <div>
          <p className="font-bold">{copy.title}</p>
          <p className="mt-1 text-xs leading-5">{copy.message}</p>
        </div>
      </div>
      {onRetry && (
        <button type="button" onClick={onRetry} className="inline-flex shrink-0 items-center gap-2 rounded-md border border-[#c9924d]/40 bg-white/70 px-3 py-2 text-xs font-bold text-[#8d5e2b] hover:bg-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          Retry
        </button>
      )}
    </div>
  );
}
