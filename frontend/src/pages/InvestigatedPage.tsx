import { useState } from "react";
import { Mail, SearchCheck, ShieldCheck, Target } from "lucide-react";
import { useNavigate } from "react-router";
import { contactCandidate, useCandidates } from "../api/candidates";
import { CandidateAvatar } from "../components/common/CandidateAvatar";
import { ApiStateNotice } from "../components/common/ApiStateNotice";
import { KeyMetricCard } from "../components/common/KeyMetricCard";
import { candidateEvidencePercent, candidateThesisPercent, displayScore, isEvidenceReady, isThesisAligned, ratioPercent } from "../data/portfolioMetrics";
import { DECISION_RUBRIC } from "../data/rubric";

export function InvestigatedPage() {
  const navigate = useNavigate();
  const investigatedQuery = useCandidates("investigating");
  const { data = [], isLoading, error, refetch } = investigatedQuery;
  const dataAvailable = investigatedQuery.data !== undefined;
  const [contacting, setContacting] = useState<string | null>(null);

  const contact = async (candidateId: string) => {
    setContacting(candidateId);
    try {
      await contactCandidate(candidateId);
      window.setTimeout(() => void refetch(), 5_000);
    } finally {
      setContacting(null);
    }
  };

  const strongThesis = data.filter(isThesisAligned).length;
  const evidenceReady = data.filter(isEvidenceReady).length;

  return (
    <div className="mx-auto max-w-[1100px] pb-10">
      <div className="mb-7">
        <div className="eyebrow mb-2">Manual outbound targeting</div>
        <h1 className="page-title">Investigated people</h1>
        <p className="page-description">Candidates researched and scored, but not automatically contacted. Contact any candidate manually.</p>
      </div>

      {dataAvailable && !isLoading && <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <KeyMetricCard icon={SearchCheck} label="Investigated" value={data.length} detail="Completed research and scoring" progress={100} progressLabel={`${data.length} profiles`} tone="blue" />
        <KeyMetricCard icon={Target} label="Thesis aligned" value={strongThesis} detail={`At least ${DECISION_RUBRIC.thesisAlignment}% thesis alignment`} progress={ratioPercent(strongThesis, data.length)} progressLabel={`${strongThesis} of ${data.length}`} tone="purple" />
        <KeyMetricCard icon={ShieldCheck} label="Evidence ready" value={evidenceReady} detail={`At least ${DECISION_RUBRIC.evidenceConfidence}% evidence confidence`} progress={ratioPercent(evidenceReady, data.length)} progressLabel={`${evidenceReady} of ${data.length}`} tone="green" />
      </div>}

      {isLoading && !dataAvailable && <ApiStateNotice loading label="investigated candidates" />}
      {error && <ApiStateNotice error={error} onRetry={() => void refetch()} label="investigated candidates" />}
      {dataAvailable && !isLoading && !error && data.length === 0 && <div className="panel rounded-lg py-16 text-center"><div className="text-sm font-bold">No investigated candidates waiting</div><p className="mt-2 text-xs text-muted">High-scoring candidates are contacted automatically; lower-scoring investigated profiles appear here.</p></div>}

      <div className="space-y-3">
        {data.map((candidate) => (
          <article key={candidate.id} className="panel rounded-lg p-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <button onClick={() => navigate(`/founders/${candidate.id}`)} className="flex min-w-0 items-center gap-3 text-left">
                <CandidateAvatar name={candidate.display_name} avatarUrl={candidate.avatar_url} className="h-11 w-11 rounded-lg bg-accent-soft font-bold text-accent" />
                <div>
                  <h2 className="text-[15px] font-bold">{candidate.display_name ?? candidate.stable_id}</h2>
                  <p className="mt-1 text-[11px] text-muted">Founder {displayScore(candidate.scores?.founder)} · Thesis {displayScore(candidateThesisPercent(candidate), true)} · Evidence {displayScore(candidateEvidencePercent(candidate), true)}</p>
                </div>
              </button>
              <button onClick={() => void contact(candidate.id)} disabled={contacting === candidate.id} className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2.5 text-xs font-bold text-white disabled:opacity-60">
                <Mail className="h-3.5 w-3.5" />{contacting === candidate.id ? "Queuing…" : "Contact"}
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
