import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, test, vi } from "vitest";

import { createTestQueryClient } from "../../test/queryClient";
import { CandidateCard } from "./CandidateCard";
import type { Candidate } from "../../types/candidate";

afterEach(cleanup);

function renderCandidate(ui: React.ReactElement, client = createTestQueryClient()) {
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

const baseCandidate: Candidate = {
  id: "test-id",
  stable_id: "founder-test",
  display_name: "Alice Chen",
  email: "alice@example.com",
  handles: { linkedin: "alice-chen" },
  consent_state: "granted",
  origin: "inbound",
  scores: {
    novelty: 0.85,
    momentum: 0.72,
    thesis_fit: 0.91,
    founder: 0.78,
    market: 0.62,
    idea_market: 0.41,
    evidence_confidence: 0.64,
  },
  latest_score_at: "2026-07-17T10:00:00Z",
  created_at: "2026-06-01T08:00:00Z",
};

const nullScoresCandidate: Candidate = {
  ...baseCandidate,
  id: "test-id-2",
  display_name: "Bob Smith",
  scores: null,
  latest_score_at: null,
};

describe("CandidateCard", () => {
  test("renders candidate name and initials", () => {
    renderCandidate(
      <CandidateCard
        candidate={baseCandidate}
        onViewFounder={() => {}}
      />,
    );

    expect(screen.getByText("Alice Chen")).toBeDefined();
    expect(screen.getByText("AC")).toBeDefined();
  });

  test("renders the cached avatar endpoint when available", () => {
    renderCandidate(
      <CandidateCard
        candidate={{ ...baseCandidate, avatar_url: "/api/v1/candidates/test-id/avatar" }}
        onViewFounder={() => {}}
      />,
    );

    const image = screen.getByAltText("Alice Chen avatar") as HTMLImageElement;
    expect(image.src).toContain("/api/v1/candidates/test-id/avatar");
  });

  test("renders inbound badge for inbound origin", () => {
    renderCandidate(
      <CandidateCard
        candidate={baseCandidate}
        onViewFounder={() => {}}
      />,
    );

    const inboundElements = screen.getAllByText("Inbound");
    expect(inboundElements.length).toBeGreaterThanOrEqual(1);
  });

  test("renders a sanitized website action with a safe external target", () => {
    renderCandidate(
      <CandidateCard
        candidate={{ ...baseCandidate, profile: { company: "Example", role: null, location: null, summary: null, website: "https://example.com", deck_url: null, deck_title: null, deck_stage: null, inbound_label: null, source_types: [], observation_count: 0, completeness: 0 } }}
        onViewFounder={() => {}}
      />,
    );

    const link = screen.getByRole("link", { name: "Website" });
    expect(link).toHaveAttribute("href", "https://example.com/");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noreferrer");
  });

  test("renders outbound badge for outbound origin", () => {
    const outbound = { ...baseCandidate, origin: "outbound" };
    renderCandidate(
      <CandidateCard
        candidate={outbound}
        onViewFounder={() => {}}
      />,
    );

    const outboundElements = screen.getAllByText("Outbound");
    expect(outboundElements.length).toBeGreaterThanOrEqual(1);
  });

  test("renders null scores gracefully", () => {
    renderCandidate(
      <CandidateCard
        candidate={nullScoresCandidate}
        onViewFounder={() => {}}
      />,
    );

    expect(screen.getByText("Bob Smith")).toBeDefined();
    expect(screen.getByText("No scores yet")).toBeDefined();
  });

  test("renders score-driven rings and an evidence bar", () => {
    const { container } = renderCandidate(
      <CandidateCard
        candidate={baseCandidate}
        onViewFounder={() => {}}
      />,
    );

    const card = within(container);
    const founderScore = card.getByRole("progressbar", { name: "Founder score" });
    const marketScore = card.getByRole("progressbar", { name: "Market score" });
    const ideaMarketScore = card.getByRole("progressbar", { name: "Idea × Market score" });
    const evidenceScore = card.getByRole("progressbar", { name: "Evidence confidence" });

    expect(founderScore.getAttribute("aria-valuenow")).toBe("78");
    expect(marketScore.getAttribute("aria-valuenow")).toBe("62");
    expect(ideaMarketScore.getAttribute("aria-valuenow")).toBe("41");
    expect(evidenceScore.getAttribute("aria-valuenow")).toBe("64");
    expect(card.getByText("Strong")).toBeDefined();
    expect(card.getByText("Risk")).toBeDefined();
  });

  test("renders fallback initial for null display_name", () => {
    const noName = { ...baseCandidate, display_name: null };
    renderCandidate(
      <CandidateCard
        candidate={noName}
        onViewFounder={() => {}}
      />,
    );

    expect(screen.getByText("?")).toBeDefined();
  });

  test("renders only functional action buttons", () => {
    renderCandidate(
      <CandidateCard
        candidate={baseCandidate}
        onViewFounder={() => {}}
      />,
    );

    const buttons = screen.getAllByRole("button");
    const buttonTexts = buttons.map((b) => b.textContent).filter(Boolean);
    expect(buttonTexts).toContain("View Founder");
    expect(buttonTexts).not.toContain("Add to Pipeline");
    expect(buttonTexts).not.toContain("Draft Outreach");
    expect(buttonTexts).toContain("Dismiss");
  });

  test("opens the outreach workflow without opening the founder profile", () => {
    const onOutreach = vi.fn();
    const onViewFounder = vi.fn();
    const { container } = renderCandidate(
      <CandidateCard candidate={baseCandidate} onViewFounder={onViewFounder} onOutreach={onOutreach} />,
    );

    fireEvent.click(within(container).getByRole("button", { name: "Outreach" }));

    expect(onOutreach).toHaveBeenCalledTimes(1);
    expect(onViewFounder).not.toHaveBeenCalled();
  });

  test("uses the explicit founder action instead of a pointer-only card", () => {
    const onViewFounder = vi.fn();
    renderCandidate(<CandidateCard candidate={baseCandidate} onViewFounder={onViewFounder} />);

    fireEvent.click(screen.getByRole("button", { name: "View Founder" }));
    expect(onViewFounder).toHaveBeenCalledOnce();
  });

  test("invalidates candidate projections after a saved dismissal", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ action: "dismiss" }), { status: 200 })));
    const queryClient = createTestQueryClient();
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
    renderCandidate(<CandidateCard candidate={baseCandidate} onViewFounder={() => {}} />, queryClient);

    fireEvent.click(screen.getAllByRole("button", { name: "Dismiss" })[1]);
    fireEvent.change(screen.getByRole("textbox", { name: "Why dismiss this candidate?" }), { target: { value: "Not in current thesis" } });
    fireEvent.click(screen.getByRole("button", { name: "Save dismissal" }));

    await waitFor(() => expect(screen.queryByText("Alice Chen")).not.toBeInTheDocument());
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["candidate", "test-id"] });
  });
});
