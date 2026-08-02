export interface FounderEvent {
  date: string;
  title: string;
  body: string;
  type: string;
  trust: number;
}

export interface FounderClaim {
  claim: string;
  source: string;
  trust: number;
  status: string;
}

export interface FounderAssessment {
  title: "Founder" | "Market" | "Idea × Market";
  rating: "Bullish" | "Neutral" | "Bearish" | "Pending";
  trend: "Improving" | "Stable" | "Declining";
  confidence: number;
  score: number | null;
  body: string;
}

export interface FounderProfile {
  stableId: string;
  initials: string;
  company: string;
  role: string;
  location: string;
  stage: string;
  sector: string;
  summary: string;
  signal: string;
  tags: string[];
  founderScore: number;
  momentum: number;
  thesisFit: number;
  evidence: number;
  scoreHint: string;
  assessments: FounderAssessment[];
  events: FounderEvent[];
  claims: FounderClaim[];
  coverage: { label: string; value: number }[];
  gaps: string[];
  relations: { label: string; sub: string; kind: "company" | "person" | "institution" | "investor"; verified: boolean }[];
  affiliations: { name: string; role: string; meta: string; kind: "company" | "work" | "education" }[];
  trendHistory: number[];
  axisTrendHistory: Record<FounderAssessment["title"], number[]>;
}
