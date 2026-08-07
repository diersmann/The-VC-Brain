import { describe, expect, it } from "vitest";
import { candidateExternalLinks, safeExternalUrl, safeHttpUrl, safeMailto } from "./candidateLinks";
import type { CandidateDetail } from "../types/candidate";

function detail(): CandidateDetail {
  return {
    id: "candidate-1",
    stable_id: "candidate-1",
    display_name: "Founder",
    email: null,
    handles: { github: "founder", twitter: "founder_x" },
    consent_state: "pending",
    origin: "inbound",
    scores: null,
    profile: {
      company: "Company",
      role: "Founder",
      location: null,
      summary: null,
      website: "https://company.example",
      deck_url: "https://company.example/deck",
      deck_title: null,
      deck_stage: null,
      inbound_label: null,
      source_types: [],
      observation_count: 2,
      completeness: 0.5,
    },
    latest_score_at: null,
    created_at: null,
    opportunity: null,
    observations: [
      {
        id: "observation-linkedin",
        predicate: "research_founder_evidence",
        object_value: "Founder profile",
        confidence: 0.9,
        observed_at: "2026-01-01T00:00:00Z",
        source_type: "tavily_search",
        source_uri: "https://www.linkedin.com/in/founder",
      },
      {
        id: "observation-github",
        predicate: "github_login",
        object_value: "founder",
        confidence: 1,
        observed_at: "2026-01-01T00:00:00Z",
        source_type: "github",
        source_uri: "https://github.com/founder",
      },
    ],
    claims: [],
    assessments: [],
    score_history: [],
    relationships: [],
  };
}

describe("candidateExternalLinks", () => {
  it("builds supported profile links without duplicates", () => {
    expect(candidateExternalLinks(detail())).toEqual([
      { kind: "linkedin", label: "LinkedIn", url: "https://www.linkedin.com/in/founder" },
      { kind: "github", label: "GitHub", url: "https://github.com/founder" },
      { kind: "website", label: "Website", url: "https://company.example/" },
      { kind: "deck", label: "Pitch deck", url: "https://company.example/deck" },
      { kind: "x", label: "X / Twitter", url: "https://x.com/founder_x" },
    ]);
  });

  it("rejects unsafe schemes and non-http claim sources", () => {
    expect(safeExternalUrl("javascript:alert(1)")).toBeNull();
    expect(safeExternalUrl("data:text/html,unsafe")).toBeNull();
    expect(safeHttpUrl("Tavily search result")).toBeNull();
    expect(safeHttpUrl("https://safe.example/source")).toBe("https://safe.example/source");
  });
});

describe("safeMailto", () => {
  it("constructs a recipient handoff and encodes subject and body", () => {
    expect(safeMailto("ada@example.com", "Hello & welcome", "Line one\nLine two")).toBe(
      "mailto:ada@example.com?subject=Hello%20%26%20welcome&body=Line%20one%0ALine%20two",
    );
  });

  it.each([
    ["", "blank recipient"],
    ["   ", "whitespace-only recipient"],
    ["ada@example.com\r\nBcc: attacker@example.com", "CR/LF injection"],
    ["not-an-email", "invalid recipient"],
    ["alice..foo@example.com", "malformed dot-atom local part"],
    ["ada?bcc=attacker@example.com", "URI query delimiter"],
    ["ada%0d%0abcc@example.com", "encoded control sequence"],
  ])("rejects %s (%s)", (recipient) => {
    expect(safeMailto(recipient, "Subject", "Body")).toBeNull();
  });

  it("rejects an overlong mailbox local part", () => {
    expect(safeMailto(`${"a".repeat(65)}@example.com`, "Subject", "Body")).toBeNull();
  });
});
