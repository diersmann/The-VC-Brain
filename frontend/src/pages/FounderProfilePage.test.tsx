import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, test, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";

import { createTestQueryClient } from "../test/queryClient";
import type { CandidateDetail } from "../types/candidate";
import { FounderProfilePage } from "./FounderProfilePage";
import { researchCandidate, useCandidate } from "../api/candidates";
import { useJobRun } from "../api/jobs";

vi.mock("../api/candidates", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/candidates")>()),
  researchCandidate: vi.fn(),
  useCandidate: vi.fn(),
}));

vi.mock("../api/jobs", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/jobs")>()),
  useJobRun: vi.fn(() => ({ data: undefined, error: null })),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const candidate: CandidateDetail = {
  id: "candidate-1",
  stable_id: "candidate-1",
  display_name: "Test Founder",
  email: "founder@example.com",
  handles: { github: "test-founder" },
  consent_state: "granted",
  origin: "outbound",
  scores: { novelty: null, momentum: 0.5, thesis_fit: 0.7, evidence_confidence: 0.5, founder: 0.6, market: 0.5, idea_market: 0.4 },
  latest_score_at: null,
  created_at: "2026-08-01T00:00:00Z",
  lifecycle_stage: "investigating",
  opportunity: { id: "opportunity-1", company_name: "Example Co", source_kind: "github", lifecycle_state: "investigating", thesis_version: "thesis-v1", created_at: null },
  observations: [],
  claims: [],
  assessments: [],
  score_history: [],
  relationships: [],
};

describe("FounderProfilePage mutation lock", () => {
  test("does not queue research twice while the first request is unresolved", () => {
    vi.mocked(useCandidate).mockReturnValue({ data: candidate, isLoading: false, error: null, refetch: vi.fn() } as never);
    vi.mocked(researchCandidate).mockReturnValue(new Promise(() => {}) as never);
    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/founders/candidate-1"]}>
          <Routes><Route path="/founders/:founderId" element={<FounderProfilePage />} /></Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const button = screen.getByRole("button", { name: "Research with Tavily" });
    fireEvent.click(button);
    fireEvent.click(button);
    expect(researchCandidate).toHaveBeenCalledTimes(1);
    expect(button).toBeDisabled();
  });

  test("refreshes candidate projections after a failed terminal research job", async () => {
    vi.mocked(useCandidate).mockReturnValue({ data: candidate, isLoading: false, error: null, refetch: vi.fn() } as never);
    vi.mocked(useJobRun).mockReturnValue({ data: { status: "failed" }, error: null } as never);
    const queryClient = createTestQueryClient();
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/founders/candidate-1"]}>
          <Routes><Route path="/founders/:founderId" element={<FounderProfilePage />} /></Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["candidate", "candidate-1"] }));
  });
});
