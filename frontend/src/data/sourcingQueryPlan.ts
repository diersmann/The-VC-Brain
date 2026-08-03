export type QueryClauseKind = "role" | "geography" | "sector" | "traction" | "exclusion" | "freshness" | "graph" | "unparsed";

export type QueryClause = {
  kind: QueryClauseKind;
  value: string;
  forwardedToSource: boolean;
};

export type SourcingQueryPlan = {
  clauses: QueryClause[];
  geography: string[];
  corrections: string[];
  downstreamClauseCount: number;
};

const geographyTerms = ["berlin", "germany", "dach", "munich", "london", "paris", "europe", "remote"];
const roleTerms = ["founder", "co-founder", "cto", "technical", "engineer", "developer"];
const sectorTerms = ["ai", "infra", "infrastructure", "saas", "fintech", "climate", "healthtech", "robotics"];
const tractionTerms = ["traction", "revenue", "customer", "customers", "enterprise", "growth", "pilot", "users"];
const graphTerms = ["accelerator", "alumni", "network", "top-tier", "top tier", "backing"];

export function buildSourcingQueryPlan(query: string): SourcingQueryPlan {
  const parts = query
    .split(/[,;]+/)
    .map((part) => part.trim())
    .filter(Boolean);
  const clauses = parts.map((value) => {
    const normalized = value.toLowerCase();
    const kind = classifyClause(normalized);
    return { kind, value, forwardedToSource: kind === "geography" };
  });
  const geography = clauses.filter((clause) => clause.kind === "geography").map((clause) => clause.value);
  const corrections = query.trim() && geography.length === 0
    ? ["Add a geography: GitHub discovery currently applies location filters at the source."]
    : [];
  return {
    clauses,
    geography,
    corrections,
    downstreamClauseCount: clauses.filter((clause) => !clause.forwardedToSource).length,
  };
}

function classifyClause(value: string): QueryClauseKind {
  if (["no ", "without ", "exclude", "excluding"].some((term) => value.includes(term))) return "exclusion";
  if (["recent", "latest", "last ", "new ", "founded this"].some((term) => value.includes(term))) return "freshness";
  if (graphTerms.some((term) => value.includes(term))) return "graph";
  if (geographyTerms.some((term) => value.includes(term))) return "geography";
  if (tractionTerms.some((term) => value.includes(term))) return "traction";
  if (sectorTerms.some((term) => value.includes(term))) return "sector";
  if (roleTerms.some((term) => value.includes(term))) return "role";
  return "unparsed";
}
