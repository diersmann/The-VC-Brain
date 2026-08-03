import { Link } from "react-router";

export function NotFoundPage() {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-[620px] flex-col items-center justify-center px-6 text-center">
      <p className="eyebrow mb-2">Page not found</p>
      <h1 className="text-2xl font-bold text-ink">That workspace does not exist.</h1>
      <p className="mt-2 text-sm leading-6 text-muted">The link may be outdated or the record may have moved. Return to the investment workspace to continue.</p>
      <Link to="/" className="mt-5 rounded-md bg-accent px-4 py-2.5 text-xs font-bold text-white">Back to workspace</Link>
    </div>
  );
}
