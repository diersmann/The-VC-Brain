import { AlertTriangle, RefreshCw } from "lucide-react";
import { Link } from "react-router";

export function RouteErrorFallback({ embedded = false, onRetry }: { embedded?: boolean; onRetry: () => void }) {
  const Container = embedded ? "section" : "main";

  return (
    <Container className="flex min-h-[60vh] items-center justify-center px-6 py-12" aria-labelledby="route-error-title">
      <div role="alert" className="panel w-full max-w-[560px] rounded-xl px-6 py-8 text-center md:px-9">
        <AlertTriangle className="mx-auto h-8 w-8 text-warn" aria-hidden="true" />
        <p className="eyebrow mt-4">Workspace unavailable</p>
        <h1 id="route-error-title" className="mt-2 text-2xl font-bold text-ink">We couldn’t load this page.</h1>
        <p className="mx-auto mt-3 max-w-[430px] text-sm leading-6 text-muted">
          Try loading the page again, or return to the workspace overview to continue.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2.5 text-xs font-bold text-white hover:bg-accent/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            Try again
          </button>
          <Link
            to="/"
            className="inline-flex items-center rounded-md border border-line-2 bg-white/70 px-4 py-2.5 text-xs font-bold text-ink-2 hover:bg-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Back to workspace
          </Link>
        </div>
      </div>
    </Container>
  );
}
