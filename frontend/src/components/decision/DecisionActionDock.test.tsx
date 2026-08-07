import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, test, vi } from "vitest";

import { createTestQueryClient } from "../../test/queryClient";
import { DecisionActionDock } from "./DecisionActionDock";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function renderDock(ui: React.ReactElement, client = createTestQueryClient()) {
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

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
    const queryClient = createTestQueryClient();
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
    renderDock(<DecisionActionDock candidateId="candidate-1" opportunityId="opportunity-1" currentState="memo_ready" onSaved={onSaved} />, queryClient);

    fireEvent.click(screen.getByRole("button", { name: "Hold" }));
    fireEvent.change(screen.getByPlaceholderText("Add a concise reason for the decision record…"), { target: { value: "Verify retention" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm Hold" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("Decision saved · hold")).toBeDefined();
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["candidates"] });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["candidate-list"] });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["candidate-list-pages"] });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["candidate", "candidate-1"] });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/candidates/candidate-1/decision",
      expect.objectContaining({ body: JSON.stringify({ opportunity_id: "opportunity-1", action: "hold", reason: "Verify retention" }) }),
    );
  });

  test("does not expose or submit decisions without a linked opportunity", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const onSaved = vi.fn();
    renderDock(<DecisionActionDock candidateId="candidate-1" opportunityId={null} currentState="investigating" onSaved={onSaved} />);

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

  test("locks the selected decision while the save is pending", async () => {
    let resolveDecision: (response: Response) => void = () => {};
    const pendingDecision = new Promise<Response>((resolve) => { resolveDecision = resolve; });
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(pendingDecision));
    const queryClient = createTestQueryClient();
    const onSaved = vi.fn();
    renderDock(<DecisionActionDock candidateId="candidate-1" opportunityId="opportunity-1" currentState="memo_ready" onSaved={onSaved} />, queryClient);

    fireEvent.click(screen.getByRole("button", { name: "Hold" }));
    fireEvent.change(screen.getByPlaceholderText("Add a concise reason for the decision record…"), { target: { value: "Verify retention" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm Hold" }));

    const savingButton = await screen.findByRole("button", { name: "Saving…" });
    expect(savingButton).toBeDisabled();
    expect(screen.getByRole("button", { name: "Proceed" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Decline" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Close decision reason" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Proceed" }));
    fireEvent.click(screen.getByRole("button", { name: "Close decision reason" }));
    expect(screen.getByRole("heading", { name: "Hold this opportunity" })).toBeInTheDocument();

    resolveDecision(new Response(JSON.stringify({
      event_id: "event-2",
      prior_state: "memo_ready",
      new_state: "hold",
      action: "hold",
      reason: "Verify retention",
      created_at: "2026-07-19T10:00:00Z",
    }), { status: 200 }));
    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
  });

  test("reuses the same idempotency key when a decision request is retried", async () => {
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new Error("connection lost"))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        event_id: "event-retry",
        prior_state: "memo_ready",
        new_state: "hold",
        action: "hold",
        reason: "Verify retention",
        created_at: "2026-07-19T10:00:00Z",
      }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const queryClient = createTestQueryClient();
    renderDock(<DecisionActionDock candidateId="candidate-1" opportunityId="opportunity-1" currentState="memo_ready" onSaved={vi.fn()} />, queryClient);

    fireEvent.click(screen.getByRole("button", { name: "Hold" }));
    fireEvent.change(screen.getByPlaceholderText("Add a concise reason for the decision record…"), { target: { value: "Verify retention" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm Hold" }));
    await waitFor(() => expect(screen.getByText("Unable to save the decision. Please retry.")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Confirm Hold" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const firstHeaders = fetchMock.mock.calls[0][1].headers as Record<string, string>;
    const secondHeaders = fetchMock.mock.calls[1][1].headers as Record<string, string>;
    expect(firstHeaders["Idempotency-Key"]).toBe(secondHeaders["Idempotency-Key"]);
  });
});
