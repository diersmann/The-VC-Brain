import type { DecisionReadiness } from "../../data/portfolioMetrics";
import { scoreViewModel } from "../../data/displayMetrics";
import { readinessVisual } from "./decisionVisualConfig";

export function DecisionStatusBadge({ state, showDetail = true }: { state: DecisionReadiness; showDetail?: boolean }) {
  const visual = readinessVisual(state);

  return (
    <div
      role="status"
      aria-label={`${visual.label}: ${visual.detail}. ${visual.explanation}`}
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
  const visual = scoreViewModel(value, "decision");
  const progress = visual.percent ?? 0;

  return (
    <div className="min-w-0">
      <div className="flex items-end justify-between gap-2">
        <span className="data-label truncate">{label}</span>
        <span className="numeric text-[15px] font-bold leading-none" style={{ color: visual.color }}>{visual.percent == null ? "—" : `${visual.percent}%`}</span>
      </div>
      <div
        className="mt-2 h-1.5 overflow-hidden rounded-full"
        aria-label={`${label}: ${visual.percent == null ? "pending" : `${visual.percent}%`}`}
        aria-valuetext={visual.explanation}
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={visual.percent ?? undefined}
        style={{ backgroundColor: visual.soft }}
      >
        <div className="h-full rounded-full transition-[width] duration-500" style={{ width: `${progress}%`, backgroundColor: visual.color }} />
      </div>
      <div className="mt-1 text-[9px] font-medium text-muted">{detail}</div>
    </div>
  );
}
