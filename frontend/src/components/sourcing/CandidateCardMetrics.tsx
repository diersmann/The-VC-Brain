import { Lightbulb, ShieldCheck, Store, UserRound } from "lucide-react";
import { confidenceViewModel, scoreViewModel } from "../../data/displayMetrics";
import type { Candidate } from "../../types/candidate";

export function CandidateCardMetrics({ candidate }: { candidate: Candidate }) {
  const evidence = candidate.scores?.evidence_confidence;
  return <><div className="grid grid-cols-3 gap-2"><Metric icon={UserRound} label="Founder" value={candidate.scores?.founder ?? candidate.scores?.raw?.founder} /><Metric icon={Store} label="Market" value={candidate.scores?.market ?? candidate.scores?.raw?.market} /><Metric icon={Lightbulb} label="Idea × Market" value={candidate.scores?.idea_market ?? candidate.scores?.raw?.idea_market} /></div><EvidenceBar value={evidence} /></>;
}

function Metric({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: number | null | undefined }) {
  const visual = scoreViewModel(value);
  const circumference = 2 * Math.PI * 26;
  const offset = circumference * (1 - (visual.percent ?? 0) / 100);
  return <div className="flex min-w-0 flex-col items-center rounded-md bg-white/70 px-2 py-3 text-center shadow-[0_6px_18px_rgba(70,91,120,.06)]"><div role="progressbar" aria-label={`${label} score`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={visual.percent ?? undefined} aria-valuetext={`${visual.percent == null ? "No score" : `${visual.percent}% · ${visual.status}`}. ${visual.explanation}`} title={visual.explanation} className="relative h-[72px] w-[72px]"><svg viewBox="0 0 72 72" className="h-full w-full -rotate-90" aria-hidden="true"><circle cx="36" cy="36" r="26" fill="none" stroke="#e7edf4" strokeWidth="7" /><circle cx="36" cy="36" r="26" fill="none" stroke={visual.color} strokeWidth="7" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset} className="transition-[stroke-dashoffset] duration-500" /></svg><div className="absolute inset-0 flex items-center justify-center"><span className="numeric text-[15px] font-bold" style={{ color: visual.color }}>{visual.percent == null ? "—" : `${visual.percent}%`}</span></div></div><div className="mt-2 flex min-w-0 items-center justify-center gap-1.5 text-[11px] font-bold text-ink-2"><span className="flex h-5 w-5 shrink-0 items-center justify-center rounded" style={{ backgroundColor: visual.soft, color: visual.color }}><Icon className="h-3 w-3" /></span><span className="truncate">{label}</span></div><span className="mt-1 text-[9px] font-bold uppercase tracking-wider" style={{ color: visual.color }}>{visual.status}</span></div>;
}

function EvidenceBar({ value }: { value: number | null | undefined }) {
  const confidence = confidenceViewModel(value);
  const visual = scoreViewModel(value);
  return <div className="mt-3 rounded-md bg-white/60 px-3 py-2.5"><div className="flex items-center justify-between gap-3"><div className="flex items-center gap-1.5 text-[10px] font-bold text-ink-2"><ShieldCheck className="h-3.5 w-3.5" style={{ color: visual.color }} /> Evidence confidence</div><div className="flex items-center gap-2"><span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: visual.color }}>{confidence.measured ? visual.status : "No score"}</span><span className="numeric text-xs font-bold" style={{ color: visual.color }}>{confidence.label === "Not scored" ? "—" : confidence.label}</span></div></div><div role="progressbar" aria-label="Evidence confidence" aria-valuemin={0} aria-valuemax={100} aria-valuenow={confidence.percent ?? undefined} aria-valuetext={confidence.percent == null ? "No score" : `${confidence.percent}% · ${visual.status}`} title={confidence.explanation} className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-3"><div className="h-full rounded-full transition-[width] duration-500" style={{ width: `${confidence.percent ?? 0}%`, backgroundColor: visual.color }} /></div></div>;
}
