import type { DecisionReadiness } from "../../data/portfolioMetrics";
import { readinessVisual } from "./decisionVisualConfig";

export function DecisionStatusBadge({ state, showDetail = true }: { state: DecisionReadiness; showDetail?: boolean }) {
  const visual = readinessVisual(state);

  return (
    <div
      role="status"
      aria-label={`${visual.label}: ${visual.detail}`}
      className="inline-flex items-center gap-2 rounded-md px-2.5 py-2"
      style={{ backgroundColor: visual.soft }}
    >
      <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: visual.color }} />
      <span>
        <span className="block text-[10px] font-bold leading-tight" style={{ color: visual.color }}>{visual.label}</span>
        {showDetail && <span className="mt-0.5 block text-[9px] font-medium text-muted">{visual.detail}</span>}
      </span>
    </div>
  );
}

export function DecisionScoreIndicator({ label, value, detail }: { label: string; value: number | null; detail: string }) {
  const visual = scoreVisual(value);
  const progress = value ?? 0;

  return (
    <div className="min-w-0">
      <div className="flex items-end justify-between gap-2">
        <span className="data-label truncate">{label}</span>
        <span className="numeric text-[15px] font-bold leading-none" style={{ color: visual.color }}>{value == null ? "—" : `${value}%`}</span>
      </div>
      <div
        className="mt-2 h-1.5 overflow-hidden rounded-full"
        aria-label={`${label}: ${value == null ? "pending" : `${value}%`}`}
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value ?? undefined}
        style={{ backgroundColor: visual.soft }}
      >
        <div className="h-full rounded-full transition-[width] duration-500" style={{ width: `${progress}%`, backgroundColor: visual.color }} />
      </div>
      <div className="mt-1 text-[9px] font-medium text-muted">{detail}</div>
    </div>
  );
}

function scoreVisual(value: number | null) {
  if (value == null) return { color: "#9aa8ba", soft: "#edf1f5" };
  if (value >= 75) return { color: "#2f8b72", soft: "#e4f2ed" };
  if (value >= 55) return { color: "#557dc0", soft: "#e7eef9" };
  if (value >= 40) return { color: "#b87932", soft: "#fff1df" };
  return { color: "#b9575f", soft: "#fbe8e9" };
}
