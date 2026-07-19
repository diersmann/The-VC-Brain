import type { DecisionReadiness } from "../../data/portfolioMetrics";

const readinessStyles = {
  ready: {
    label: "Ready for review",
    detail: "Thesis and evidence cleared",
    color: "#2f8b72",
    soft: "#e4f2ed",
  },
  investigate: {
    label: "Investigate",
    detail: "Human scrutiny required",
    color: "#557dc0",
    soft: "#e7eef9",
  },
  "evidence-gap": {
    label: "Evidence gap",
    detail: "Collect decision-critical proof",
    color: "#b87932",
    soft: "#fff1df",
  },
} satisfies Record<DecisionReadiness, { label: string; detail: string; color: string; soft: string }>;

export function readinessVisual(state: DecisionReadiness) {
  return readinessStyles[state];
}
