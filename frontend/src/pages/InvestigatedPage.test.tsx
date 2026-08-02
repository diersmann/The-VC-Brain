import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { MemoryRouter } from "react-router";

import { InvestigatedPage } from "./InvestigatedPage";
import { TestQueryProvider } from "../test/queryClient";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const candidate = {
  id: "candidate-1",
  stable_id: "candidate-1",
  display_name: "Test Founder",
  email: "founder@example.com",
  handles: { github: "test-founder" },
  consent_state: "granted",
  origin: "outbound",
  lifecycle_stage: "investigating",
  scores: { novelty: 0.8, momentum: 0.8, thesis_fit: 0.8, evidence_confidence: 0.8, founder: 0.8, market: 0.8, idea_market: 0.8 },
  latest_score_at: null,
  created_at: null,
};

describe("InvestigatedPage mutation states", () => {
  test("surfaces contact queue failures and leaves the action retryable", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([candidate]), { status: 200 }))
      .mockRejectedValueOnce(new Error("API unavailable"));
    vi.stubGlobal("fetch", fetchMock);

    render(<TestQueryProvider><MemoryRouter><InvestigatedPage /></MemoryRouter></TestQueryProvider>);
    fireEvent.click(await screen.findByRole("button", { name: "Contact" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to queue contact");
    expect(screen.getByRole("button", { name: "Contact" })).not.toBeDisabled();
  });
});
