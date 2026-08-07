import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, ExternalLink, Send, Sparkles } from "lucide-react";
import { invalidateCandidateQueries, recordCandidateFeedback } from "../../api/candidates";
import { formatPredicate } from "../../data/candidateProfile";
import { safeExternalUrl } from "../../data/candidateLinks";
import type { Candidate } from "../../types/candidate";
import { CandidateCardHeader } from "./CandidateCardHeader";
import { CandidateCardMetrics } from "./CandidateCardMetrics";

interface Props {
  candidate: Candidate;
  onViewFounder: () => void;
  onOutreach?: () => void;
}

export function CandidateCard({ candidate, onViewFounder, onOutreach }: Props) {
  const queryClient = useQueryClient();
  const [dismissed, setDismissed] = useState(false);
  const [dismissReason, setDismissReason] = useState("");
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackState, setFeedbackState] = useState<"idle" | "saving" | "error">("idle");
  if (dismissed) return null;

  const profile = candidate.profile;
  const websiteUrl = safeExternalUrl(profile?.website);
  const originTone = candidate.origin === "inbound" ? "bg-[#ece9fb] text-[#7059a6]" : candidate.origin === "outbound" ? "bg-[#e4f3ee] text-[#327d68]" : "bg-accent-soft text-accent";

  return <article className="panel group rounded-lg p-5 transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_18px_45px_rgba(65,90,125,.13)]">
    <CandidateCardHeader candidate={candidate} originTone={originTone} onDismiss={() => setFeedbackOpen(true)} />
    <div className="my-4 rounded-md bg-gradient-to-br from-surface-2 to-[#edf2f8] p-3.5"><div className="flex gap-2"><Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-accent" /><div><div className="data-label">Evidence summary</div><p className="mt-1.5 line-clamp-3 text-[13px] leading-5 text-ink-2">{profile?.summary || `Public activity was collected from ${formatPredicate(Object.keys(candidate.handles ?? {})[0] ?? candidate.origin ?? "database")}, but a verified founder summary is still pending.`}</p></div></div></div>
    {!candidate.scores && <div className="mb-2 text-[11px] font-semibold text-warn">No scores yet</div>}
    <CandidateCardMetrics candidate={candidate} />
    <div className="mt-3 flex flex-wrap items-center gap-2 text-[10px] font-semibold text-muted"><span className="rounded-full bg-white/80 px-2.5 py-1">{profile?.observation_count ?? 0} observations</span><span className="rounded-full bg-white/80 px-2.5 py-1">{profile?.source_types.length ?? 0} source types</span><span className="rounded-full bg-white/80 px-2.5 py-1">{Math.round((profile?.completeness ?? 0) * 100)}% complete</span></div>
    <div className="mt-4 flex flex-wrap gap-1.5">{(profile?.source_types ?? Object.keys(candidate.handles ?? {})).map((tag) => <span key={tag} className="rounded-full bg-white/75 px-2.5 py-1 text-[10px] font-medium text-muted shadow-sm">{formatPredicate(tag)}</span>)}{websiteUrl && <a href={websiteUrl} target="_blank" rel="noreferrer" onClick={(event) => event.stopPropagation()} className="inline-flex items-center gap-1 rounded-full bg-accent-soft px-2.5 py-1 text-[10px] font-bold text-accent">Website <ExternalLink className="h-3 w-3" /></a>}</div>
    <div className="mt-4 flex flex-wrap items-center gap-3 rounded-md bg-surface-2/70 px-3 py-2.5">{onOutreach && <button onClick={(event) => { event.stopPropagation(); onOutreach(); }} className="inline-flex items-center gap-1.5 text-xs font-bold text-accent"><Send className="h-3.5 w-3.5" /> Outreach</button>}<button onClick={(event) => { event.stopPropagation(); setFeedbackOpen(true); }} className="text-xs font-semibold text-muted hover:text-danger">Dismiss</button><button onClick={onViewFounder} className="ml-auto flex items-center gap-1 text-xs font-bold text-accent">View Founder<ArrowUpRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5" /></button></div>
    {feedbackOpen && <div className="mt-3 rounded-md border border-line bg-white p-3" onClick={(event) => event.stopPropagation()}><label htmlFor={`dismiss-reason-${candidate.id}`} className="text-xs font-semibold text-ink-2">Why dismiss this candidate?</label><textarea id={`dismiss-reason-${candidate.id}`} value={dismissReason} onChange={(event) => setDismissReason(event.target.value)} className="mt-2 min-h-16 w-full rounded-md border border-line bg-surface-2 p-2 text-xs outline-none focus:border-accent-muted" placeholder="Record a review reason" />{feedbackState === "error" && <p className="mt-1 text-xs font-semibold text-danger">Unable to save feedback. Try again.</p>}<div className="mt-2 flex justify-end gap-2"><button type="button" onClick={() => setFeedbackOpen(false)} className="rounded-md px-3 py-1.5 text-xs font-semibold text-muted">Cancel</button><button type="button" disabled={feedbackState === "saving" || dismissReason.trim().length < 3} onClick={async () => { setFeedbackState("saving"); try { await recordCandidateFeedback(candidate.id, "dismiss", dismissReason.trim()); setDismissed(true); void invalidateCandidateQueries(queryClient, candidate.id); } catch { setFeedbackState("error"); } }} className="rounded-md bg-accent px-3 py-1.5 text-xs font-bold text-white disabled:opacity-40">{feedbackState === "saving" ? "Saving…" : "Save dismissal"}</button></div></div>}
  </article>;
}
