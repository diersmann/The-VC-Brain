import type { CandidateDetail, CandidateObservation } from "../types/candidate";
import type { FounderAssessment, FounderClaim, FounderProfile } from "../types/profile";

const axisNames: FounderAssessment["title"][] = ["Founder", "Market", "Idea × Market"];

export function buildFounderProfile(candidate: CandidateDetail): FounderProfile {
  const observations = candidate.observations;
  const sources = unique(observations.map((item) => item.source_type));
  const company = candidate.opportunity?.company_name ?? observationValue(observations, ["company", "company_name", "github_company"]) ?? "No company linked";
  const location = observationValue(observations, ["location", "github_location", "city", "country"]) ?? "Location not available";
  const role = observationValue(observations, ["role", "title", "headline", "position"]) ?? "Founder candidate";
  const about = observationValue(observations, ["research_founder_summary", "bio", "about", "hn_about", "github_bio", "page_summary", "page_content"]);
  const sourceLabel = sources.length ? sources.map(formatPredicate).join(", ") : "No source evidence";
  const composite = scoreValue(candidate, "composite");
  const founderScore = percentage(scoreValue(candidate, "founder") ?? composite);
  const momentum = percentage(scoreValue(candidate, "momentum") ?? composite);
  const thesisFit = percentage(scoreValue(candidate, "thesis_fit"));
  const sourceConfidence = observations.length
    ? Math.round(observations.reduce((sum, item) => sum + item.confidence, 0) / observations.length * 100)
    : null;
  const coverage = buildCoverage(observations);
  const coverageScore = observations.length
    ? Math.round(coverage.reduce((sum, item) => sum + item.value, 0) / coverage.length)
    : null;
  const trendHistory = candidate.score_history
    .map((snapshot) => numeric(snapshot.components.composite ?? snapshot.components.founder ?? snapshot.components.thesis_fit))
    .filter((value): value is number => value !== null)
    .map(percentage);
  const axisTrendHistory: FounderProfile["axisTrendHistory"] = {
    Founder: scoreHistory(candidate, "founder"),
    Market: scoreHistory(candidate, "market"),
    "Idea × Market": scoreHistory(candidate, "idea_market"),
  };

  const assessments = axisNames.map((title) => {
    const axisKey = title === "Founder" ? "founder" : title === "Market" ? "market" : "idea_market";
    const actual = candidate.assessments.find((item) => normalizeAxis(item.axis) === title);
    if (!actual) {
      return {
        title,
        rating: "Pending" as const,
        trend: "Stable" as const,
        confidence: 0,
        score: null,
        body: `No recorded ${title} assessment yet. Review the collected evidence before assigning a rating.`,
      };
    }
    return {
      title,
      rating: normalizeRating(actual.rating),
      trend: normalizeTrend(actual.trend),
      confidence: percentage(actual.confidence),
      score: scoreValue(candidate, axisKey) == null
        ? null
        : percentage(scoreValue(candidate, axisKey)),
      body: actual.unknowns.length ? `Open questions: ${actual.unknowns.join("; ")}` : "Assessment recorded from the investment workflow.",
    };
  });

  const reconciledClaims = candidate.claims.map((claim) => ({
        claim: `${formatPredicate(claim.predicate)}: ${claim.object_value}`,
        source: "Reconciled claim",
        trust: percentage(claim.trust_score ?? claim.confidence),
        status: formatClaimStatus(claim.status),
      }));
  const sourceEvidence = observations
    .filter((item) => /^research_.*_evidence$/.test(item.predicate))
    .map((item) => ({
        claim: `${formatPredicate(item.predicate)}: ${truncate(item.object_value, 150)}`,
        source: item.source_uri,
        trust: percentage(item.confidence),
        status: "Observed" as const,
      }));
  const evidenceClaims = [...reconciledClaims, ...sourceEvidence].length
    ? [...reconciledClaims, ...sourceEvidence].slice(0, 12)
    : observations.slice(0, 6).map((item) => ({
        claim: `${formatPredicate(item.predicate)}: ${truncate(item.object_value, 150)}`,
        source: item.source_uri,
        trust: percentage(item.confidence),
        status: "Observed" as const,
      }));

  const gaps = unique([
    ...candidate.assessments.flatMap((item) => item.unknowns),
    ...(candidate.email ? [] : ["Verified contact information is missing"]),
    ...(candidate.opportunity ? [] : ["No investment opportunity is linked to this person"]),
    ...(thesisFit > 0 ? [] : ["Thesis fit has not been scored"]),
  ]).slice(0, 6);

  return {
    stableId: candidate.stable_id,
    initials: initials(candidate.display_name),
    company,
    role,
    location,
    stage: candidate.opportunity?.lifecycle_state ? formatPredicate(candidate.opportunity.lifecycle_state) : "Discovery",
    sector: observationValue(observations, ["sector", "industry", "category"]) ?? sourceLabel,
    summary: about ? truncate(stripHtml(about), 420) : `Public profile collected from ${sourceLabel}. ${observations.length} source observations are available for review.`,
    signal: signalText(observations, composite, sourceLabel),
    tags: unique([...sources.map(formatPredicate), ...Object.keys(candidate.handles ?? {}).map(formatPredicate)]).slice(0, 6),
    founderScore,
    momentum,
    thesisFit,
    evidence: sourceConfidence ?? 0,
    sourceConfidence,
    coverageScore,
    scoreHint: `${observations.length} observations across ${sources.length} source${sources.length === 1 ? "" : "s"}`,
    assessments,
    events: observations.slice(0, 8).map((item) => ({
      date: formatDate(item.observed_at),
      title: formatPredicate(item.predicate),
      body: truncate(stripHtml(item.object_value), 220),
      type: formatPredicate(item.source_type),
      trust: percentage(item.confidence),
    })),
    claims: evidenceClaims,
    coverage,
    gaps,
    relations: candidate.relationships.map((item) => ({
      label: item.display_name ?? item.person_id,
      sub: formatPredicate(item.relationship_type),
      kind: "person" as const,
      verified: item.confidence >= 0.8,
    })),
    affiliations: candidate.opportunity ? [{
      name: candidate.opportunity.company_name,
      role,
      meta: `${formatPredicate(candidate.opportunity.lifecycle_state)} · ${candidate.opportunity.source_kind}`,
      kind: "company" as const,
    }] : [],
    trendHistory,
    axisTrendHistory,
  };
}

export function candidateSignal(candidate: CandidateDetail | { scores: CandidateDetail["scores"] }): number | null {
  return scoreValue(candidate, "composite");
}

export function percentage(value: number | null | undefined): number {
  if (value == null || Number.isNaN(value)) return 0;
  return Math.round(value <= 1 ? value * 100 : value);
}

export function initials(name: string | null): string {
  return (name ?? "?").split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
}

export function formatPredicate(value: string): string {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function formatDate(value: string | null): string {
  if (!value) return "Unknown date";
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}

function observationValue(observations: CandidateObservation[], predicates: string[]): string | null {
  const keys = predicates.map((item) => item.toLowerCase());
  return observations.find((item) => keys.includes(item.predicate.toLowerCase()))?.object_value ?? null;
}

function scoreValue(candidate: { scores: CandidateDetail["scores"] }, key: string): number | null {
  const direct = candidate.scores?.[key as keyof NonNullable<CandidateDetail["scores"]>];
  if (typeof direct === "number") return direct;
  const raw = candidate.scores?.raw?.[key];
  return typeof raw === "number" ? raw : null;
}

function numeric(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}

function scoreHistory(candidate: CandidateDetail, key: string): number[] {
  return candidate.score_history
    .map((snapshot) => numeric(snapshot.components[key]))
    .filter((value): value is number => value !== null)
    .map(percentage);
}

function normalizeAxis(axis: string): FounderAssessment["title"] | null {
  const value = axis.toLowerCase().replace(/[_-]/g, " ");
  if (value.includes("founder")) return "Founder";
  if (value.includes("idea") || value.includes("fit")) return "Idea × Market";
  if (value.includes("market")) return "Market";
  return null;
}

function normalizeRating(rating: string): FounderAssessment["rating"] {
  const value = rating.toLowerCase();
  if (value === "bullish") return "Bullish";
  if (value === "bearish") return "Bearish";
  return "Neutral";
}

function normalizeTrend(trend: string): FounderAssessment["trend"] {
  const value = trend.toLowerCase();
  if (value === "improving") return "Improving";
  if (value === "declining") return "Declining";
  return "Stable";
}

function formatClaimStatus(status: CandidateDetail["claims"][number]["status"]): FounderClaim["status"] {
  if (status === "supported") return "Supported";
  if (status === "contradicted") return "Contradicted";
  if (status === "tavily_synthesized") return "Synthesized";
  return "Unverified";
}

function signalText(observations: CandidateObservation[], composite: number | null, sourceLabel: string): string {
  const activity = observationValue(observations, ["github_total_stars", "hn_total_points", "producthunt_total_upvotes", "arxiv_total_citations"]);
  if (activity) return `Public activity signal: ${activity} (${sourceLabel})`;
  if (composite != null) return `Composite discovery signal ${percentage(composite)}% from ${sourceLabel}`;
  return `Evidence collected from ${sourceLabel}; investment scoring is pending.`;
}

function buildCoverage(observations: CandidateObservation[]): { label: string; value: number }[] {
  const groups = [
    { label: "Identity & background", keys: ["name", "bio", "about", "location", "company", "title"] },
    { label: "Product & technical", keys: ["repo", "star", "language", "product", "project", "story"] },
    { label: "Commercial traction", keys: ["revenue", "customer", "launch", "upvote", "growth"] },
    { label: "Market evidence", keys: ["market", "sector", "industry", "category"] },
  ];
  return groups.map((group) => {
    const matches = observations.filter((item) => group.keys.some((key) => item.predicate.toLowerCase().includes(key)));
    const confidence = matches.length ? matches.reduce((sum, item) => sum + item.confidence, 0) / matches.length : 0;
    return { label: group.label, value: Math.min(100, Math.round(matches.length * 12 + confidence * 40)) };
  });
}

function truncate(value: string, length: number): string {
  return value.length > length ? `${value.slice(0, length - 1)}…` : value;
}

function stripHtml(value: string): string {
  return value.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

function unique<T>(values: T[]): T[] {
  return [...new Set(values)];
}
