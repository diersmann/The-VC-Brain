import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

import type { CandidateDetail } from "../../types/candidate";
import { InvestmentMemo } from "./InvestmentMemo";

afterEach(cleanup);

const candidate: CandidateDetail = {
  id: "candidate-1",
  stable_id: "candidate-1",
  display_name: "Test Founder",
  email: "founder@example.com",
  handles: null,
  consent_state: "unknown",
  origin: "inbound",
  scores: null,
  latest_score_at: null,
  created_at: null,
  opportunity: null,
  observations: [{ id: "observation-1", predicate: "github_bio", object_value: "Builds reliable infrastructure.", confidence: 0.8, source_locator: { page: 2 }, observed_at: "2025-01-02T00:00:00Z", source_type: "github", source_uri: "https://github.com/example" }],
  claims: [{ id: "claim-1", predicate: "founder_role", object_value: "Founder", status: "supported", confidence: 0.85, trust_score: 0.9, trust_interval: { low: 0.8, high: 0.95 }, trust_components: null, trust_explanation: "Direct source with corroboration.", created_at: null }],
  assessments: [],
  score_history: [],
  relationships: [],
};

describe("InvestmentMemo provenance", () => {
  test("opens validated claim and observation references", () => {
    render(<InvestmentMemo candidate={candidate} memo={{ sections: [{ title: "Company snapshot", text: "A concise memo.", claim_ids: ["claim-1"], evidence_ids: ["observation-1"] }], status: "succeeded", generation_mode: "template", model_version: null, created_at: null }} memoError={null} memoLoading={false} memoGenState="idle" onGenerate={() => undefined} onRetryMemo={() => undefined} />);

    fireEvent.click(screen.getByText("Open 2 provenance references"));

    expect(screen.getByText("Direct source with corroboration.")).toBeInTheDocument();
    expect(screen.getByText("Coordinates: {\"page\":2}")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open source" })).toHaveAttribute("href", "https://github.com/example");
  });
});
