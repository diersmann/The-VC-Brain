/** Candidate DTO matching the backend GET /api/v1/candidates response. */

export interface CandidateScores {
  novelty: number | null;
  momentum: number | null;
  thesis_fit: number | null;
  evidence_confidence: number | null;
  raw?: Record<string, number> | null;
}

export interface Candidate {
  id: string;
  stable_id: string;
  display_name: string | null;
  email: string | null;
  handles: Record<string, string> | null;
  consent_state: string;
  origin: string | null;
  scores: CandidateScores | null;
  latest_score_at: string | null;
  created_at: string | null;
}

/** The four nav sections in the app shell. */
export type ViewId = "sourcing" | "memo" | "thesis" | "settings";
