import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { DecisionActionDock } from "./DecisionActionDock";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("DecisionActionDock", () => {
  test("collects a reason and persists a hold decision", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        event_id: "event-1",
        prior_state: "memo_ready",
        new_state: "hold",
        action: "hold",
        reason: "Verify retention",
        created_at: "2026-07-19T10:00:00Z",
      }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const onSaved = vi.fn();
    render(<DecisionActionDock candidateId="candidate-1" opportunityId="opportunity-1" currentState="memo_ready" onSaved={onSaved} />);

    fireEvent.click(screen.getByRole("button", { name: "Hold" }));
    fireEvent.change(screen.getByPlaceholderText("Add a concise reason for the decision record…"), { target: { value: "Verify retention" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm Hold" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("Decision saved · hold")).toBeDefined();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/candidates/candidate-1/decision",
      expect.objectContaining({ body: JSON.stringify({ opportunity_id: "opportunity-1", action: "hold", reason: "Verify retention" }) }),
    );
  });

  test("does not expose or submit decisions without a linked opportunity", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const onSaved = vi.fn();
    render(<DecisionActionDock candidateId="candidate-1" opportunityId={null} currentState="investigating" onSaved={onSaved} />);

    for (const label of ["Proceed", "Hold", "Decline"]) {
      const button = screen.getByRole("button", { name: label });
      expect(button).toBeDisabled();
      expect(button).toHaveAttribute("title", "No opportunity is linked to this candidate");
      fireEvent.click(button);
    }

    expect(fetchMock).not.toHaveBeenCalled();
    expect(onSaved).not.toHaveBeenCalled();
    expect(screen.queryByText(/Decision saved/)).not.toBeInTheDocument();
  });
});
