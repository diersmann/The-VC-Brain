import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { InvestmentWorkflowTree } from "./InvestmentWorkflowTree";

const lifecycle = {
  version: "unified-v2",
  stages: [
    "received", "triage", "investigating", "screening", "diligence", "memo_ready", "approved", "closed",
  ].map((key) => ({
    key,
    label: key === "memo_ready" ? "Memo ready" : key === "approved" ? "Approved" : key[0].toUpperCase() + key.slice(1),
    lane: "inbound",
    entry_requirements: [],
    exit_requirements: [],
    actors: [],
    transitions: [],
    timestamp_source:
      "Opportunity.created_at for initial entry; DecisionEvent.created_at for transitions",
  })),
};

describe("InvestmentWorkflowTree", () => {
  test("renders the unified lifecycle with live counts and navigable nodes", () => {
    const onNavigate = vi.fn();
    render(
      <InvestmentWorkflowTree
        thesisName="Berlin Deep Tech"
        thesisVersion="v3"
        counts={{ inbound: 4, outbound: 8, total: 12, scored: 9, pending: 3, highSignal: 5 }}
        lifecycle={lifecycle}
        onNavigate={onNavigate}
      />,
    );

    expect(screen.getByText("4 records")).toBeDefined();
    expect(screen.getByText("8 profiles")).toBeDefined();
    expect(screen.getAllByText("12 opportunities").length).toBe(2);
    expect(screen.getAllByText("Investigating · Founder · Market · Idea × Market · 3 pending").length).toBe(2);
    expect(screen.getAllByText(/Screening & Diligence/).length).toBe(2);
    expect(screen.getAllByRole("button", { name: /approved \/ closed feedback/i })).toHaveLength(2);
    expect(screen.getAllByRole("button", { name: /approved \/ closed feedback/i })[0]).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: /founder applications/i }));
    fireEvent.click(screen.getAllByRole("button", { name: /memo ready & decision/i })[0]);

    expect(onNavigate).toHaveBeenNthCalledWith(1, "/inbound");
    expect(onNavigate).toHaveBeenNthCalledWith(2, "/decisions");
  });
});
