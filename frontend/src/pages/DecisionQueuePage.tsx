import { AlertTriangle, ArrowRight, Clock3, Scale, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router";
import { useCandidates } from "../api/candidates";
import { CandidateAvatar } from "../components/common/CandidateAvatar";
import { formatDate, formatPredicate, percentage } from "../data/candidateProfile";
import type { Candidate } from "../types/candidate";

export function DecisionQueuePage() {
  const navigate = useNavigate();
  const { data = [], isLoading, error } = useCandidates();
  const scored = data.filter((candidate) => decisionScore(candidate) !== null);
  const highSignal = data.filter((candidate) => (decisionScore(candidate) ?? 0) >= 45);
  const pending = data.filter((candidate) => !candidate.scores).length;

  return (
    <div className="mx-auto max-w-[1100px] pb-10">
      <div className="mb-7">
        <div className="eyebrow mb-2">Human approval</div>
        <h1 className="text-3xl font-bold tracking-tight">Decision queue</h1>
        <p className="mt-2 text-sm text-muted">Live candidates ordered by available database evidence.</p>
      </div>

      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <QueueMetric icon={Scale} label="Scored profiles" value={String(scored.length)} tone="blue" />
        <QueueMetric icon={ShieldCheck} label="Above signal threshold" value={String(highSignal.length)} tone="green" />
        <QueueMetric icon={Clock3} label="Awaiting score" value={String(pending)} tone="amber" />
      </div>

      {isLoading && <div className="py-16 text-center text-sm text-muted">Loading decision candidates…</div>}
      {error && <div className="rounded-md bg-[#fff1df] p-4 text-xs text-[#a96e2d]">Unable to load the live decision queue.</div>}
      {!isLoading && !error && data.length === 0 && (
        <div className="panel rounded-lg py-16 text-center">
          <div className="text-sm font-bold">No candidates available</div>
          <p className="mt-2 text-xs text-muted">Run founder discovery before starting investment review.</p>
        </div>
      )}

      <div className="space-y-3">
        {data.map((candidate) => {
          const score = decisionScore(candidate);
          const source = Object.keys(candidate.handles ?? {})[0] ?? candidate.origin ?? "database";
          return (
            <article
              key={candidate.id}
              onClick={() => navigate(`/decisions/${candidate.id}`)}
              className="panel cursor-pointer rounded-lg p-5 transition-all hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center">
                <div className="flex min-w-[220px] items-center gap-3">
                  <CandidateAvatar name={candidate.display_name} avatarUrl={candidate.avatar_url} className="h-11 w-11 rounded-lg bg-accent-soft font-bold text-accent" />
                  <div>
                    <h2 className="text-sm font-bold">{candidate.display_name ?? candidate.stable_id}</h2>
                    <p className="text-[11px] text-muted">{formatPredicate(source)} · Added {formatDate(candidate.created_at)}</p>
                  </div>
                </div>
                <div className="grid flex-1 grid-cols-2 gap-3 md:grid-cols-4">
                  <Datum label="Thesis match" value={candidate.scores?.thesis_fit == null ? "Not scored" : `${percentage(candidate.scores.thesis_fit)}%`} icon={ShieldCheck} />
                  <Datum label="Review status" value={recommendation(candidate)} icon={Scale} />
                  <Datum label="Evidence" value={candidate.scores?.evidence_confidence == null ? "Collecting" : `${percentage(candidate.scores.evidence_confidence)}%`} icon={AlertTriangle} />
                  <Datum label="Discovery signal" value={score == null ? "Pending" : `${score}%`} icon={Clock3} />
                </div>
                <button type="button" className="flex items-center justify-center gap-1 rounded-md bg-accent px-4 py-2.5 text-xs font-bold text-white">Review <ArrowRight className="h-3.5 w-3.5" /></button>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function decisionScore(candidate: Candidate): number | null {
  const value = candidate.scores?.thesis_fit ?? candidate.scores?.raw?.composite ?? candidate.scores?.momentum;
  return value == null ? null : percentage(value);
}

function recommendation(candidate: Candidate): string {
  const thesis = candidate.scores?.thesis_fit;
  if (thesis != null && thesis >= 0.75) return "Ready for review";
  const score = decisionScore(candidate);
  if (score != null && score >= 45) return "Investigate";
  return "Collect evidence";
}

function QueueMetric({ icon: Icon, label, value, tone }: { icon: React.ElementType; label: string; value: string; tone: "blue" | "amber" | "green" }) {
  const tones = { blue: "bg-[#e7eef9] text-[#5074a8]", amber: "bg-[#fff1df] text-[#a96e2d]", green: "bg-[#e4f2ed] text-[#347c67]" };
  return <div className="panel flex items-center gap-3 rounded-lg p-4"><span className={`flex h-10 w-10 items-center justify-center rounded-md ${tones[tone]}`}><Icon className="h-4 w-4" /></span><div><div className="text-lg font-bold">{value}</div><div className="text-[10px] text-muted">{label}</div></div></div>;
}

function Datum({ label, value, icon: Icon }: { label: string; value: string; icon: React.ElementType }) {
  return <div><div className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider text-muted-2"><Icon className="h-3 w-3" />{label}</div><div className="mt-1 truncate text-[11px] font-semibold text-ink-2">{value}</div></div>;
}
