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
  test("opens reviewed outreach instead of queuing contact directly", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([candidate]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    render(<TestQueryProvider><MemoryRouter><InvestigatedPage /></MemoryRouter></TestQueryProvider>);
    fireEvent.click(await screen.findByRole("button", { name: "Review contact" }));

    expect(await screen.findByRole("dialog", { name: "Draft outreach to Test Founder" })).toBeInTheDocument();
    expect(screen.getByText(/Provenance:/)).toBeInTheDocument();
    expect(screen.getByText("granted")).toBeInTheDocument();
    expect(screen.getByText(/Provider state:/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledOnce();
  });
});
