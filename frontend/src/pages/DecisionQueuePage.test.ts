import { describe, expect, it } from "vitest";
import { sortDecisionCandidates } from "../data/decisionQueue";
import type { Candidate } from "../types/candidate";

function candidate(
  name: string,
  scores: Partial<NonNullable<Candidate["scores"]>>,
  createdAt: string,
): Candidate {
  return {
    id: name,
    stable_id: name.toLowerCase(),
    display_name: name,
    email: null,
    handles: null,
    consent_state: "pending",
    origin: "inbound",
    scores: {
      novelty: null,
      momentum: null,
      thesis_fit: null,
      evidence_confidence: null,
      ...scores,
    },
    latest_score_at: null,
    created_at: createdAt,
  };
}

const candidates = [
  candidate("Beta", { thesis_fit: 0.4, founder: 0.9 }, "2026-01-01T00:00:00Z"),
  candidate("Alpha", { thesis_fit: 0.8, founder: 0.5 }, "2026-02-01T00:00:00Z"),
  candidate("Gamma", {}, "2026-03-01T00:00:00Z"),
];

describe("sortDecisionCandidates", () => {
  it("sorts score fields descending and places missing scores last", () => {
    expect(sortDecisionCandidates(candidates, "thesis").map((item) => item.display_name)).toEqual(["Alpha", "Beta", "Gamma"]);
    expect(sortDecisionCandidates(candidates, "founder").map((item) => item.display_name)).toEqual(["Beta", "Alpha", "Gamma"]);
  });

  it("sorts by newest and founder name", () => {
    expect(sortDecisionCandidates(candidates, "newest").map((item) => item.display_name)).toEqual(["Gamma", "Alpha", "Beta"]);
    expect(sortDecisionCandidates(candidates, "name").map((item) => item.display_name)).toEqual(["Alpha", "Beta", "Gamma"]);
  });
});
