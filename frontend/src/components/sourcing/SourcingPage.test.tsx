import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { MemoryRouter } from "react-router";

import { TestQueryProvider } from "../../test/queryClient";
import { SourcingPage } from "./SourcingPage";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const candidate = {
  id: "candidate-1",
  stable_id: "candidate-1",
  display_name: "Test Founder",
  email: null,
  handles: { github: "test-founder" },
  consent_state: "unknown",
  origin: "outbound",
  scores: { novelty: 0.8, momentum: 0.8, thesis_fit: 0.8, evidence_confidence: 0.8, founder: 0.8, market: 0.8, idea_market: 0.8 },
  latest_score_at: null,
  created_at: null,
};

describe("SourcingPage mutation states", () => {
  test("surfaces discovery queue failures without losing the query", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([candidate]), { status: 200 }))
      .mockRejectedValueOnce(new Error("API unavailable")));

    render(<TestQueryProvider><MemoryRouter><SourcingPage /></MemoryRouter></TestQueryProvider>);
    const query = await screen.findByRole("textbox", { name: "Discovery query" });
    const originalQuery = (query as HTMLInputElement).value;
    expect(screen.getByLabelText("Sourcing query plan")).toHaveTextContent("GitHub location filter: Berlin");

    fireEvent.click(screen.getByRole("button", { name: "Discover live" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to queue discovery");
    expect(query).toHaveValue(originalQuery);
  });
});
