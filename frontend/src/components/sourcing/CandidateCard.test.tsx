import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { CandidateCard } from "./CandidateCard";
import type { Candidate } from "../../types/candidate";

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
    render(
      <CandidateCard
        candidate={baseCandidate}
        onViewFounder={() => {}}
        onAddPipeline={() => {}}
      />,
    );

    expect(screen.getByText("Alice Chen")).toBeDefined();
    expect(screen.getByText("AC")).toBeDefined();
  });

  test("renders the cached avatar endpoint when available", () => {
    render(
      <CandidateCard
        candidate={{ ...baseCandidate, avatar_url: "/api/v1/candidates/test-id/avatar" }}
        onViewFounder={() => {}}
        onAddPipeline={() => {}}
      />,
    );

    const image = screen.getByAltText("Alice Chen avatar") as HTMLImageElement;
    expect(image.src).toContain("/api/v1/candidates/test-id/avatar");
  });

  test("renders inbound badge for inbound origin", () => {
    render(
      <CandidateCard
        candidate={baseCandidate}
        onViewFounder={() => {}}
        onAddPipeline={() => {}}
      />,
    );

    const inboundElements = screen.getAllByText("Inbound");
    expect(inboundElements.length).toBeGreaterThanOrEqual(1);
  });

  test("renders outbound badge for outbound origin", () => {
    const outbound = { ...baseCandidate, origin: "outbound" };
    render(
      <CandidateCard
        candidate={outbound}
        onViewFounder={() => {}}
        onAddPipeline={() => {}}
      />,
    );

    const outboundElements = screen.getAllByText("Outbound");
    expect(outboundElements.length).toBeGreaterThanOrEqual(1);
  });

  test("renders null scores gracefully", () => {
    render(
      <CandidateCard
        candidate={nullScoresCandidate}
        onViewFounder={() => {}}
        onAddPipeline={() => {}}
      />,
    );

    expect(screen.getByText("Bob Smith")).toBeDefined();
    expect(screen.getByText("No scores yet")).toBeDefined();
  });

  test("renders fallback initial for null display_name", () => {
    const noName = { ...baseCandidate, display_name: null };
    render(
      <CandidateCard
        candidate={noName}
        onViewFounder={() => {}}
        onAddPipeline={() => {}}
      />,
    );

    expect(screen.getByText("?")).toBeDefined();
  });

  test("renders action buttons", () => {
    render(
      <CandidateCard
        candidate={baseCandidate}
        onViewFounder={() => {}}
        onAddPipeline={() => {}}
      />,
    );

    const buttons = screen.getAllByRole("button");
    const buttonTexts = buttons.map((b) => b.textContent).filter(Boolean);
    expect(buttonTexts).toContain("View Founder");
    expect(buttonTexts).toContain("Add to Pipeline");
    expect(buttonTexts).toContain("Draft Outreach");
    expect(buttonTexts).toContain("Dismiss");
  });
});
