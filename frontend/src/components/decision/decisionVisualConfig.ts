import type { DecisionReadiness } from "../../data/portfolioMetrics";
import { readinessViewModel } from "../../data/displayMetrics";

export function readinessVisual(state: DecisionReadiness) {
  return readinessViewModel(state);
}
