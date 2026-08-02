import { Building2, CheckCircle2, MapPin, X } from "lucide-react";
import { formatPredicate } from "../../data/candidateProfile";
import type { Candidate } from "../../types/candidate";
import { CandidateAvatar } from "../common/CandidateAvatar";

export function CandidateCardHeader({ candidate, originTone, onDismiss }: { candidate: Candidate; originTone: string; onDismiss: () => void }) {
  const profile = candidate.profile;
  const source = Object.keys(candidate.handles ?? {})[0] ?? candidate.origin ?? "database";
  const handle = Object.values(candidate.handles ?? {})[0];
  return <div className="flex items-start gap-3"><CandidateAvatar name={candidate.display_name} avatarUrl={candidate.avatar_url} className="h-12 w-12 rounded-lg bg-gradient-to-br from-[#dce6f2] to-[#c6d3e3] text-sm font-bold text-accent ring-2 ring-white shadow-sm" /><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h3 className="truncate text-[15px] font-bold leading-tight">{candidate.display_name ?? candidate.stable_id}</h3>{candidate.consent_state === "granted" && <CheckCircle2 className="h-3.5 w-3.5 text-success" />}<span className={`status-pill ${originTone}`}>{candidate.origin === "inbound" ? "Inbound" : candidate.origin === "outbound" ? "Outbound" : "Discovered"}</span></div><div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted"><span className="inline-flex items-center gap-1 font-medium text-ink-2"><Building2 className="h-3 w-3 text-[#6f8db7]" />{profile?.company?.replace(/^@/, "") || "Company not disclosed"}</span><span className="inline-flex items-center gap-1"><MapPin className="h-3 w-3 text-[#c27a5b]" />{profile?.location || "Location not disclosed"}</span></div><div className="mt-1 text-[10px] text-muted">{formatPredicate(source)}{handle ? ` · ${handle}` : ""}</div></div><button aria-label="Dismiss" onClick={(event) => { event.stopPropagation(); onDismiss(); }} className="rounded-md p-1.5 text-muted-2 hover:bg-surface-2"><X className="h-4 w-4" /><span className="sr-only">Dismiss</span></button></div>;
}
