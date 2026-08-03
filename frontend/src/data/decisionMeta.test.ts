import { describe, expect, it } from "vitest";

import { buildFounderProfile } from "./candidateProfile";
import { createDecisionMeta } from "./decisionMeta";
import type { CandidateDetail, CandidateSLA } from "../types/candidate";

function candidate(sla?: CandidateSLA): CandidateDetail {
  return {
    id: "candidate-1",
    stable_id: "founder-1",
    display_name: "Ada Founder",
    email: null,
    handles: null,
    consent_state: "pending",
    origin: "inbound",
    scores: null,
    latest_score_at: null,
    created_at: "2026-08-03T10:00:00Z",
    lifecycle_stage: "received",
    sla,
    opportunity: null,
    observations: [],
    claims: [],
    assessments: [],
    score_history: [],
    relationships: [],
  };
}

describe("createDecisionMeta SLA display", () => {
  it("uses the persisted countdown and exposes risk state", () => {
    const sla: CandidateSLA = {
      received_at: "2026-08-03T10:00:00Z",
      decision_due_at: "2026-08-04T10:00:00Z",
      stage_deadlines: {},
      owner: null,
      pause_reason: null,
      stage: "triage",
      status: "at_risk",
      attainment: "pending",
      remaining_seconds: 5400,
      stage_remaining_seconds: 0,
      elapsed_seconds: 81000,
      alert: true,
      alert_level: "warning",
    };

    const meta = createDecisionMeta(buildFounderProfile(candidate(sla)), candidate(sla));

    expect(meta.deadline).toBe("1h 30m");
    expect(meta.slaStatus).toBe("at_risk");
    expect(meta.slaAlert).toBe(true);
    expect(meta.slaStage).toBe("triage");
    expect(meta.slaOwner).toBe("Unassigned");
  });

  it("does not invent a schedule when the backend has not started the clock", () => {
    const meta = createDecisionMeta(buildFounderProfile(candidate()), candidate());

    expect(meta.deadline).toBe("Not scheduled");
    expect(meta.slaStatus).toBe("not_started");
    expect(meta.slaAlert).toBe(false);
  });

  it("uses the persisted proposal for recommendation, risks, and conditions", () => {
    const detail = candidate();
    detail.decision_proposal = {
      id: "proposal-1",
      action: "investigate",
      status: "draft",
      check_amount: null,
      ownership_target: null,
      conviction: "medium",
      founder_assessment_id: "assessment-founder",
      market_assessment_id: "assessment-market",
      idea_market_assessment_id: "assessment-idea-market",
      top_evidence: ["claim-1"],
      top_risks: ["Market size needs primary validation"],
      open_conditions: ["Resolve: Market size needs primary validation"],
      readiness_blockers: [],
      readiness_status: "ready",
      thesis_version: "thesis-v3",
      rubric_versions: ["decision-proposal-v1"],
      memo_model_version: "gpt-test",
      override_reason: null,
      created_at: "2026-08-03T10:00:00Z",
    };

    const meta = createDecisionMeta(buildFounderProfile(detail), detail);

    expect(meta.recommendation).toBe("Investigate");
    expect(meta.risks).toEqual(["Market size needs primary validation"]);
    expect(meta.conditions).toEqual(["Resolve: Market size needs primary validation"]);
    expect(meta.conviction).toBe("medium");
  });
});
