import { useMemo, useState } from "react";
import { AlertTriangle, ArrowDownUp, ChevronRight, Scale, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router";
import { useCandidates } from "../api/candidates";
import { CandidateAvatar } from "../components/common/CandidateAvatar";
import { DecisionScoreIndicator, DecisionStatusBadge } from "../components/decision/DecisionVisuals";
import { KeyMetricCard } from "../components/common/KeyMetricCard";
import { formatDate, formatPredicate } from "../data/candidateProfile";
import { buildDecisionBrief, sortDecisionCandidates, type DecisionSort } from "../data/decisionQueue";
import { candidateDecisionScore, candidateEvidencePercent, candidateThesisPercent, decisionReadiness, ratioPercent } from "../data/portfolioMetrics";

export function DecisionQueuePage() {
  const navigate = useNavigate();
  const { data = [], isLoading, error } = useCandidates();
  const [sortBy, setSortBy] = useState<DecisionSort>("thesis");
  const sortedCandidates = useMemo(() => sortDecisionCandidates(data, sortBy), [data, sortBy]);
  const ready = data.filter((candidate) => decisionReadiness(candidate) === "ready").length;
  const investigate = data.filter((candidate) => decisionReadiness(candidate) === "investigate").length;
  const evidenceGaps = data.filter((candidate) => decisionReadiness(candidate) === "evidence-gap").length;

  return (
    <div className="mx-auto max-w-[1100px] pb-10">
      <div className="mb-7">
        <div className="eyebrow mb-2">Human approval</div>
        <h1 className="page-title">Decision queue</h1>
        <p className="page-description">Live candidates ordered by available database evidence.</p>
      </div>

      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <KeyMetricCard icon={ShieldCheck} label="Ready for review" value={ready} detail="Strong thesis fit backed by sufficient evidence" progress={ratioPercent(ready, data.length)} progressLabel={`${ready} of ${data.length} opportunities`} tone="green" />
        <KeyMetricCard icon={Scale} label="Investigate" value={investigate} detail="Promising signal that still needs investor scrutiny" progress={ratioPercent(investigate, data.length)} progressLabel={`${investigate} of ${data.length} opportunities`} tone="blue" />
        <KeyMetricCard icon={AlertTriangle} label="Evidence gaps" value={evidenceGaps} detail="Insufficient signal for a defensible decision" progress={ratioPercent(evidenceGaps, data.length)} progressLabel={`${evidenceGaps} of ${data.length} opportunities`} tone="amber" />
      </div>

      {isLoading && <div className="py-16 text-center text-sm text-muted">Loading decision candidates…</div>}
      {error && <div className="rounded-md bg-[#fff1df] p-4 text-xs text-[#a96e2d]">Unable to load the live decision queue.</div>}
      {!isLoading && !error && data.length === 0 && (
        <div className="panel rounded-lg py-16 text-center">
          <div className="text-sm font-bold">No candidates available</div>
          <p className="mt-2 text-xs text-muted">Run founder discovery before starting investment review.</p>
        </div>
      )}

      {!isLoading && !error && data.length > 0 && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-lg bg-white/60 px-4 py-3 shadow-[0_8px_24px_rgba(70,91,120,.06)] backdrop-blur-xl">
          <span className="text-[11px] font-semibold text-muted"><span className="numeric">{sortedCandidates.length}</span> candidates · missing values appear last</span>
          <label className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-muted-2">
            <ArrowDownUp className="h-3.5 w-3.5 text-accent" /> Sort by
            <select value={sortBy} onChange={(event) => setSortBy(event.target.value as DecisionSort)} className="rounded-md bg-white px-3 py-2 text-xs font-semibold normal-case tracking-normal text-ink shadow-sm outline-none focus:ring-2 focus:ring-accent/20">
              <option value="thesis">Thesis match · high to low</option>
              <option value="founder">Founder score · high to low</option>
              <option value="market">Market score · high to low</option>
              <option value="idea-market">Idea × Market · high to low</option>
              <option value="newest">Newest added</option>
              <option value="name">Founder name · A–Z</option>
            </select>
          </label>
        </div>
      )}

      <div className="space-y-3">
        {sortedCandidates.map((candidate) => {
          const thesisScore = candidateThesisPercent(candidate);
          const evidenceScore = candidateEvidencePercent(candidate);
          const discoveryScore = candidateDecisionScore(candidate);
          const readiness = decisionReadiness(candidate);
          const source = Object.keys(candidate.handles ?? {})[0] ?? candidate.origin ?? "database";
          return (
            <article
              key={candidate.id}
              onClick={() => navigate(`/decisions/${candidate.id}`)}
              className="panel group cursor-pointer rounded-lg p-4 transition-all hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-3">
                  <CandidateAvatar name={candidate.display_name} avatarUrl={candidate.avatar_url} className="h-11 w-11 rounded-lg bg-accent-soft font-bold text-accent" />
                  <div>
                    <h2 className="text-[15px] font-bold leading-tight">{candidate.display_name ?? candidate.stable_id}</h2>
                    <p className="mt-1 text-[10px] font-semibold uppercase tracking-[.08em] text-muted-2">{formatPredicate(source)}</p>
                    <p className="mt-1 text-[10px] text-muted">Added {formatDate(candidate.created_at)}</p>
                  </div>
                </div>
                <DecisionStatusBadge state={readiness} showDetail={false} />
              </div>
              <div className="mt-4 grid gap-5 lg:grid-cols-[minmax(280px,1fr)_minmax(340px,.9fr)_20px] lg:items-center">
                <div className="min-w-0">
                  <div className="data-label">AI investment brief</div>
                  <p className="mt-1.5 text-[11px] leading-[1.65] text-ink-2">{buildDecisionBrief(candidate)}</p>
                </div>
                <div className="grid grid-cols-3 gap-5">
                  <DecisionScoreIndicator label="Thesis match" value={thesisScore} detail="Strategy fit" />
                  <DecisionScoreIndicator label="Evidence" value={evidenceScore} detail="Source quality" />
                  <DecisionScoreIndicator label="Decision signal" value={discoveryScore} detail="Available score" />
                </div>
                <ChevronRight className="h-5 w-5 text-muted-2 transition-transform group-hover:translate-x-1 group-hover:text-accent" />
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
