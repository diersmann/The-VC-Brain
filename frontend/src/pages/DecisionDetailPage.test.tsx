import { cleanup, render, screen } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, test, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";

import { createTestQueryClient } from "../test/queryClient";
import type { CandidateDetail } from "../types/candidate";
import { RootLayout } from "../components/layout/RootLayout";
import { DecisionDetailPage } from "./DecisionDetailPage";
import { useCandidate, useCandidateMemo } from "../api/candidates";
import { useJobRun } from "../api/jobs";

vi.mock("../api/candidates", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/candidates")>()),
  useCandidate: vi.fn(),
  useCandidateMemo: vi.fn(),
}));

vi.mock("../api/jobs", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/jobs")>()),
  useJobRun: vi.fn(),
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
  origin: "inbound",
  scores: { novelty: null, momentum: 0.5, thesis_fit: 0.7, evidence_confidence: 0.5, founder: 0.6, market: 0.5, idea_market: 0.4 },
  latest_score_at: null,
  created_at: "2026-08-01T00:00:00Z",
  lifecycle_stage: "memo_ready",
  opportunity: { id: "opportunity-1", company_name: "Example Co", source_kind: "inbound", lifecycle_state: "memo_ready", thesis_version: "thesis-v1", created_at: null },
  observations: [],
  claims: [],
  assessments: [],
  score_history: [],
  relationships: [],
};

describe("DecisionDetailPage route semantics", () => {
  test("keeps the shell as the only main landmark", () => {
    vi.mocked(useCandidate).mockReturnValue({ data: candidate, isLoading: false, error: null, refetch: vi.fn() } as never);
    vi.mocked(useCandidateMemo).mockReturnValue({ data: null, isLoading: false, error: null, refetch: vi.fn() } as never);
    vi.mocked(useJobRun).mockReturnValue({ data: undefined, error: null } as never);

    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/decisions/candidate-1"]}>
          <Routes>
            <Route element={<RootLayout />}>
              <Route path="/decisions/:founderId" element={<DecisionDetailPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getAllByRole("main")).toHaveLength(1);
    expect(screen.getByRole("main").querySelector("main")).not.toBeInTheDocument();
  });
});
