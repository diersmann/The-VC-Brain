import { AlertTriangle, ArrowLeft, CheckCircle2, Clock3 } from "lucide-react";
import { Link, useParams } from "react-router";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchCandidateMemo, generateCandidateMemo, useCandidate } from "../api/candidates";
import { isTerminalJobStatus, useJobRun } from "../api/jobs";
import { ApiStateNotice } from "../components/common/ApiStateNotice";
import { DecisionActionDock } from "../components/decision/DecisionActionDock";
import { AxisScreening } from "../components/decision/DecisionEvidence";
import { DecisionDetailSidebar } from "../components/decision/DecisionDetailSidebar";
import { AiSummary, DealMetrics, EvidenceCard, ListCard } from "../components/decision/DecisionDetailSummary";
import { InvestmentMemo } from "../components/decision/InvestmentMemo";
import { buildFounderProfile } from "../data/candidateProfile";
import { createDecisionMeta } from "../data/decisionMeta";

export function DecisionDetailPage() {
  const { founderId } = useParams();
  const { data: candidate, isLoading, error, refetch } = useCandidate(founderId);
  const [memoGenState, setMemoGenState] = useState<"idle" | "queued" | "error" | "degraded">("idle");
  const [memoJobId, setMemoJobId] = useState<string | null>(null);
  const memoJob = useJobRun(memoJobId ?? undefined);
  const { data: memo, error: memoError, isLoading: memoLoading, refetch: refetchMemo } = useQuery({
    queryKey: ["candidate-memo", founderId],
    queryFn: ({ signal }) => fetchCandidateMemo(founderId!, candidate?.opportunity?.id ?? "", signal),
    enabled: Boolean(founderId && candidate?.opportunity?.id),
    staleTime: 30_000,
  });
  const memoDisplayError = memoError ?? memoJob.error;
  const memoJobStatus = memoJob.data?.status;
  const memoJobResultStatus = typeof memoJob.data?.result?.status === "string" ? memoJob.data.result.status : null;

  useEffect(() => {
    if (!isTerminalJobStatus(memoJobStatus)) return;
    if (memoJobStatus === "succeeded") {
      setMemoGenState("idle");
      void refetchMemo();
    } else if (memoJobStatus === "degraded" || memoJobResultStatus === "degraded") {
      setMemoGenState("degraded");
      void refetchMemo();
    } else {
      setMemoGenState("error");
    }
  }, [memoJobStatus, memoJobResultStatus, refetchMemo]);

  if (isLoading && !candidate) return <div className="py-20 text-center text-sm text-muted">Loading investment evidence…</div>;
  if (error && !candidate) return <div className="mx-auto max-w-[680px] py-20"><ApiStateNotice error={error} onRetry={() => void refetch()} label="decision evidence" /><Link to="/decisions" className="mt-4 inline-block text-xs font-bold text-accent">Back to decision queue</Link></div>;
  if (!candidate) return <div className="py-20 text-center"><div className="text-sm font-bold">Decision record unavailable</div><Link to="/decisions" className="mt-3 inline-block text-xs font-bold text-accent">Back to decision queue</Link></div>;

  const profile = buildFounderProfile(candidate);
  const meta = createDecisionMeta(profile, candidate);
  const generateMemo = async () => {
    setMemoGenState("queued");
    setMemoJobId(null);
    try {
      if (!candidate.opportunity?.id) return;
      const response = await generateCandidateMemo(founderId!, candidate.opportunity.id);
      setMemoJobId(response.job_id);
      if (!response.job_id) setMemoGenState("error");
    } catch {
      setMemoGenState("error");
    }
  };

  return <div className="mx-auto max-w-[1240px] pb-28">
    {error && <div className="mb-5"><ApiStateNotice error={error} onRetry={() => void refetch()} label="decision evidence" /></div>}
    <div className="mb-5 flex flex-wrap items-center justify-between gap-3"><Link to="/decisions" className="inline-flex items-center gap-2 text-xs font-bold text-muted transition-colors hover:text-ink"><ArrowLeft className="h-4 w-4" /> Back to decision queue</Link><div className={`flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.1em] ${meta.slaAlert ? "text-danger" : "text-muted"}`} role="status" aria-label={`Decision SLA: ${meta.slaStatus}`}><Clock3 className={`h-3.5 w-3.5 ${meta.slaAlert ? "text-danger" : "text-amber-600"}`} /> Decision SLA · {meta.deadline}</div></div>
    <div className="grid items-start gap-5 lg:grid-cols-[270px_minmax(0,1fr)]"><DecisionDetailSidebar profile={profile} candidate={candidate} meta={meta} /><main className="min-w-0 space-y-5"><AiSummary profile={profile} meta={meta} /><DealMetrics profile={profile} meta={meta} /><AxisScreening profile={profile} /><InvestmentMemo candidate={candidate} memo={memo} memoError={memoDisplayError} memoLoading={memoLoading} memoGenState={memoGenState} onGenerate={generateMemo} onRetryMemo={() => { void refetchMemo(); void memoJob.refetch(); }} /><div className="grid gap-5 xl:grid-cols-2"><ListCard title="Key risks" eyebrow="Downside case" icon={AlertTriangle} items={meta.risks} tone="amber" /><ListCard title="Conditions to proceed" eyebrow="Next diligence" icon={CheckCircle2} items={meta.conditions} tone="blue" /></div><EvidenceCard profile={profile} /></main></div>
    <DecisionActionDock candidateId={candidate.id} opportunityId={candidate.opportunity?.id ?? null} currentState={candidate.opportunity?.lifecycle_state ?? "No opportunity state"} onSaved={() => void refetch()} />
  </div>;
}
