/** Candidate DTO matching the backend GET /api/v1/candidates response. */

export interface CandidateScores {
  novelty: number | null;
  momentum: number | null;
  thesis_fit: number | null;
  founder?: number | null;
  market?: number | null;
  idea_market?: number | null;
  discovery_signal?: number | null;
  evidence_confidence: number | null;
  raw?: Record<string, number> | null;
}

export interface CandidateProfileSummary {
  company: string | null;
  role: string | null;
  location: string | null;
  summary: string | null;
  website: string | null;
  source_types: string[];
  observation_count: number;
  completeness: number;
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
  profile?: CandidateProfileSummary | null;
  avatar_url?: string | null;
  avatar_source?: string | null;
  latest_score_at: string | null;
  created_at: string | null;
}

export interface CandidateObservation {
  predicate: string;
  object_value: string;
  confidence: number;
  observed_at: string;
  source_type: string;
  source_uri: string;
}

export interface CandidateClaim {
  predicate: string;
  object_value: string;
  status: string;
  confidence: number;
  created_at: string | null;
}

export interface CandidateAssessment {
  axis: string;
  rating: string;
  trend: string;
  confidence: number;
  unknowns: string[];
  created_at: string | null;
}

export interface CandidateScoreSnapshot {
  rubric_version: string;
  components: Record<string, unknown>;
  created_at: string | null;
}

export interface CandidateRelationship {
  relationship_type: string;
  person_id: string;
  display_name: string | null;
  confidence: number;
  observed_at: string;
}

export interface CandidateOpportunity {
  id: string;
  company_name: string;
  source_kind: string;
  lifecycle_state: string;
  thesis_version: string | null;
  created_at: string | null;
}

export interface CandidateDetail extends Candidate {
  opportunity: CandidateOpportunity | null;
  observations: CandidateObservation[];
  claims: CandidateClaim[];
  assessments: CandidateAssessment[];
  score_history: CandidateScoreSnapshot[];
  relationships: CandidateRelationship[];
}

/** The four nav sections in the app shell. */
export type ViewId = "sourcing" | "memo" | "thesis" | "settings";
