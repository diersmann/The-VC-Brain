import { useNavigate } from "react-router";
import { AlertTriangle, ArrowRight, CheckCircle2, CircleGauge, ShieldCheck, Target } from "lucide-react";
import { useCandidates } from "../api/candidates";
import { useActiveThesis } from "../api/theses";
import { CandidateAvatar } from "../components/common/CandidateAvatar";
import { ApiStateNotice } from "../components/common/ApiStateNotice";
import { KeyMetricCard } from "../components/common/KeyMetricCard";
import { InvestmentWorkflowTree } from "../components/overview/InvestmentWorkflowTree";
import { formatDate, formatPredicate, percentage } from "../data/candidateProfile";
import { candidateThesisPercent, decisionReadiness, hasDecisionScore, median, ratioPercent } from "../data/portfolioMetrics";

export function HomePage() {
  const navigate = useNavigate();
  const candidatesQuery = useCandidates();
  const thesisQuery = useActiveThesis();
  const data = candidatesQuery.data ?? [];
  const candidateDataAvailable = candidatesQuery.data !== undefined;
  const thesisDataAvailable = thesisQuery.data !== undefined;
  const activeThesis = thesisQuery.data ?? null;
  const inbound = data.filter((candidate) => candidate.origin === "inbound");
  const outbound = data.filter((candidate) => candidate.origin === "outbound");
  const scored = data.filter(hasDecisionScore);
  const highSignal = data.filter((candidate) => (candidate.scores?.thesis_fit ?? candidate.scores?.raw?.composite ?? 0) >= 0.45);
  const reviewReady = data.filter((candidate) => decisionReadiness(candidate) === "ready");
  const thesisScores = data.map(candidateThesisPercent);
  const measuredThesisScores = thesisScores.filter((value): value is number => value !== null);
  const medianThesis = median(thesisScores);
  const scoringCoverage = ratioPercent(scored.length, data.length);
  const priorities = [...data].sort((a, b) => score(b) - score(a)).slice(0, 4);
  const thesisItems = activeThesis ? [
    activeThesis.sectors.map(thesisLabel).join(" · "),
    activeThesis.stages.map(thesisLabel).join(" / "),
    activeThesis.regions.map(thesisLabel).join(" & "),
    formatCheckRange(activeThesis.check_size_min_k_eur, activeThesis.check_size_max_k_eur),
  ] : [];

  const thesisTitle = thesisQuery.isPending ? "Loading thesis" : thesisQuery.error ? "Thesis unavailable" : activeThesis?.name ?? "Configure thesis";
  const candidateDashboardReady = candidateDataAvailable && !candidatesQuery.isPending;

  return (
    <div className="mx-auto max-w-[1220px] pb-10">
      <section className="mb-7 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div><div className="eyebrow mb-2">Investment workspace</div><h1 className="page-title">Good morning, Sophie</h1><p className="page-description">Live sourcing and decision data from the FirstCheck24 database.</p></div>
        <button onClick={() => navigate("/thesis")} className="flex w-fit items-center gap-3 rounded-md bg-white/75 px-4 py-2.5 shadow-[0_8px_24px_rgba(70,91,120,.08)] backdrop-blur-xl"><span className={`h-2 w-2 rounded-full ${activeThesis ? "bg-success" : "bg-warn"}`} /><div className="text-left"><div className="text-xs font-bold">{thesisTitle}</div><div className="text-[10px] text-muted">{activeThesis ? `${activeThesis.version} · active` : thesisQuery.error ? "Request failed" : thesisQuery.isPending ? "Loading…" : "No active thesis"}</div></div><ArrowRight className="h-3.5 w-3.5 text-muted" /></button>
      </section>

      {candidatesQuery.isPending && !candidateDataAvailable && <ApiStateNotice loading label="pipeline data" />}
      {candidatesQuery.error && <ApiStateNotice error={candidatesQuery.error} onRetry={() => void candidatesQuery.refetch()} label="pipeline data" />}

      {candidateDashboardReady && <InvestmentWorkflowTree
        thesisName={activeThesis?.name ?? "Configure thesis"}
        thesisVersion={activeThesis?.version}
        counts={{
          inbound: inbound.length,
          outbound: outbound.length,
          total: data.length,
          scored: scored.length,
          pending: data.length - scored.length,
          highSignal: highSignal.length,
        }}
        onNavigate={navigate}
      />}

      {candidateDashboardReady && <div className="mb-6 grid gap-3 sm:grid-cols-3">
        <KeyMetricCard icon={ShieldCheck} label="Review ready" value={reviewReady.length} detail="Thesis fit ≥75% with sufficient evidence" progress={ratioPercent(reviewReady.length, data.length)} progressLabel={`${reviewReady.length} of ${data.length} opportunities`} tone="green" />
        <KeyMetricCard icon={Target} label="Median thesis fit" value={medianThesis} suffix="%" detail="Central strategy-fit score across assessed deals" progress={medianThesis} progressLabel={`${measuredThesisScores.length} opportunities measured`} tone="purple" />
        <KeyMetricCard icon={CircleGauge} label="Scoring coverage" value={scoringCoverage} suffix="%" detail="Share of the pipeline with a decision signal" progress={scoringCoverage} progressLabel={`${scored.length} of ${data.length} profiles`} tone="blue" />
      </div>}

      <div className={`grid gap-5 ${candidateDashboardReady ? "xl:grid-cols-[1.6fr_1fr]" : ""}`}>
        {candidateDashboardReady && <section className="panel space-y-1 rounded-lg p-2">
          <div className="flex items-center justify-between rounded-md bg-gradient-to-r from-[#edf3fb] to-transparent px-3 py-3"><div><h2 className="section-title">Priority candidates</h2><p className="supporting-text">Ordered by recorded thesis or discovery signal</p></div><button onClick={() => navigate("/investigated")} className="text-xs font-bold text-accent">View all</button></div>
          {priorities.length === 0 && <div className="px-3 py-10 text-center text-xs text-muted">No live candidates yet.</div>}
          {priorities.map((candidate, index) => {
            const source = Object.keys(candidate.handles ?? {})[0] ?? candidate.origin ?? "database";
            return (
              <button key={candidate.id} onClick={() => navigate(`/founders/${candidate.id}`)} className="grid w-full items-center gap-3 rounded-md px-3 py-3.5 text-left transition-colors hover:bg-white/65 sm:grid-cols-[1.2fr_.8fr_1.2fr_auto]">
                <div className="flex items-center gap-3"><CandidateAvatar name={candidate.display_name} avatarUrl={candidate.avatar_url} className={`h-9 w-9 rounded-md text-xs font-bold ${tone(["amber", "blue", "purple", "green"][index % 4])}`} /><div><div className="text-[13px] font-bold leading-tight">{candidate.display_name ?? candidate.stable_id}</div><div className="mt-1 text-[11px] text-muted">{formatPredicate(source)} · {candidate.origin ?? "unclassified"}</div></div></div>
                <Cell label="Thesis match" value={candidate.scores?.thesis_fit == null ? "Not scored" : `${percentage(candidate.scores.thesis_fit)}%`} />
                <div><div className="data-label">Next action</div><div className="mt-1 flex items-center gap-1 text-xs font-semibold text-ink-2"><AlertTriangle className="h-3.5 w-3.5 text-warn" />{candidate.scores ? "Review evidence" : "Complete scoring"}</div></div>
                <span className="numeric text-[10px] text-muted">{formatDate(candidate.created_at)}</span>
              </button>
            );
          })}
        </section>}
        <section className="panel rounded-lg p-5"><div className="mb-5 flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-md bg-accent-soft text-accent"><Target className="h-4 w-4" /></span><div><h2 className="section-title">Active thesis</h2><p className="supporting-text">{activeThesis?.name ?? (thesisQuery.error ? "Thesis unavailable" : thesisQuery.isPending ? "Loading thesis…" : "Not configured")}</p></div></div>{thesisQuery.isPending && !thesisDataAvailable && <ApiStateNotice loading label="active thesis" />}{thesisQuery.error && <ApiStateNotice error={thesisQuery.error} onRetry={() => void thesisQuery.refetch()} label="active thesis" />}{!thesisQuery.isPending && !thesisQuery.error && activeThesis && thesisItems.map((item) => <div key={item} className="mb-2 flex items-center gap-2 rounded-md bg-white/60 px-3 py-2.5 text-xs font-semibold leading-5 shadow-sm"><CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-success" />{item}</div>)}{!thesisQuery.isPending && !thesisQuery.error && activeThesis === null && <div className="rounded-md bg-white/60 px-3 py-3 text-xs text-muted">No active thesis is configured. This is an empty configuration state, not a score.</div>}<button onClick={() => navigate("/thesis")} className="mt-4 flex items-center gap-1 text-xs font-bold text-accent">Edit thesis <ArrowRight className="h-3.5 w-3.5" /></button></section>
      </div>
    </div>
  );
}

function score(candidate: { scores: { thesis_fit: number | null; raw?: Record<string, number> | null } | null }): number {
  return percentage(candidate.scores?.thesis_fit ?? candidate.scores?.raw?.composite);
}
function thesisLabel(value: string): string { return value === "ai" ? "AI" : value === "b2b" ? "B2B" : value === "dach" ? "DACH" : formatPredicate(value); }
function formatCheckRange(minimum: number | null, maximum: number | null): string { if (minimum == null && maximum == null) return "Check size not set"; if (maximum == null) return `€${minimum}k+`; return `€${minimum ?? 0}k – €${maximum}k`; }
function tone(color: string) { return color === "purple" ? "bg-[#eee8f8] text-[#7656a5]" : color === "green" ? "bg-[#e4f2ed] text-[#347c67]" : color === "amber" ? "bg-[#fff1df] text-[#a96e2d]" : "bg-[#e7eef9] text-[#5074a8]"; }
function Cell({ label, value }: { label: string; value: string }) { return <div><div className="data-label">{label}</div><div className="data-value numeric">{value}</div></div>; }
