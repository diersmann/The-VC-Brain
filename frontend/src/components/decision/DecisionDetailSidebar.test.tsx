import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import { MemoryRouter } from "react-router";

import { buildFounderProfile } from "../../data/candidateProfile";
import { createDecisionMeta } from "../../data/decisionMeta";
import type { CandidateDetail } from "../../types/candidate";
import { DecisionDetailSidebar } from "./DecisionDetailSidebar";

afterEach(cleanup);

const candidate: CandidateDetail = {
  id: "candidate-1",
  stable_id: "candidate-1",
  display_name: "Test Founder",
  email: "founder@example.com",
  handles: null,
  consent_state: "granted",
  origin: "inbound",
  scores: { novelty: null, momentum: null, thesis_fit: 0.7, evidence_confidence: 0.5, founder: 0.6, market: 0.5, idea_market: 0.4 },
  latest_score_at: null,
  created_at: "2026-08-01T00:00:00Z",
  lifecycle_stage: "investigating",
  opportunity: { id: "opportunity-1", company_name: "Example Co", source_kind: "inbound", lifecycle_state: "investigating", thesis_version: "thesis-v1", created_at: null },
  observations: [],
  claims: [],
  assessments: [],
  score_history: [],
  relationships: [],
};

function candidateWithDeck(deckUrl: string | null): CandidateDetail {
  return {
    ...candidate,
    profile: {
      company: "Example Co",
      role: "Founder",
      location: "Berlin",
      summary: null,
      website: null,
      deck_url: deckUrl,
      deck_title: "Pitch deck",
      deck_stage: null,
      inbound_label: null,
      source_types: [],
      observation_count: 0,
      completeness: 0,
    },
  };
}

function renderSidebar(candidateOverride: CandidateDetail) {
  const profile = buildFounderProfile(candidateOverride);
  const meta = createDecisionMeta(profile, candidateOverride);
  render(
    <MemoryRouter>
      <DecisionDetailSidebar profile={profile} candidate={candidateOverride} meta={meta} />
    </MemoryRouter>,
  );
}

describe("DecisionDetailSidebar deck links", () => {
  test("renders a safe HTTP deck destination with an external target", () => {
    renderSidebar(candidateWithDeck("https://example.com/pitch-deck.pdf"));

    const link = screen.getByRole("link", { name: "Open pitch deck" });
    expect(link).toHaveAttribute("href", "https://example.com/pitch-deck.pdf");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noreferrer");
  });

  test.each(["javascript:alert(1)", "", null])("does not render unsafe or missing deck destinations as links (%s)", (deckUrl) => {
    renderSidebar(candidateWithDeck(deckUrl));

    expect(screen.queryByRole("link", { name: "Open pitch deck" })).not.toBeInTheDocument();
  });
});
