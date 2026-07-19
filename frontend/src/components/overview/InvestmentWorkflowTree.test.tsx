import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { InvestmentWorkflowTree } from "./InvestmentWorkflowTree";

describe("InvestmentWorkflowTree", () => {
  test("renders the unified lifecycle with live counts and navigable nodes", () => {
    const onNavigate = vi.fn();
    render(
      <InvestmentWorkflowTree
        thesisName="Berlin Deep Tech"
        thesisVersion="v3"
        counts={{ inbound: 4, outbound: 8, total: 12, scored: 9, pending: 3, highSignal: 5 }}
        onNavigate={onNavigate}
      />,
    );

    expect(screen.getByText("4 records")).toBeDefined();
    expect(screen.getByText("8 profiles")).toBeDefined();
    expect(screen.getAllByText("12 opportunities").length).toBe(2);
    expect(screen.getAllByText("Founder · Market · Idea × Market · 3 pending").length).toBe(2);

    fireEvent.click(screen.getByRole("button", { name: /founder applications/i }));
    fireEvent.click(screen.getAllByRole("button", { name: /memo & decision/i })[0]);

    expect(onNavigate).toHaveBeenNthCalledWith(1, "/inbound");
    expect(onNavigate).toHaveBeenNthCalledWith(2, "/decisions");
  });
});
