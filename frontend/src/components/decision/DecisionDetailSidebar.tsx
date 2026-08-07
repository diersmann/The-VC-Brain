import { Building2, ExternalLink, FileText, Mail, MapPin, Target } from "lucide-react";
import { Link } from "react-router";
import { CandidateAvatar } from "../common/CandidateAvatar";
import { SafeLink } from "../common/SafeLink";
import { safeExternalUrl } from "../../data/candidateLinks";
import type { CandidateDetail } from "../../types/candidate";
import type { FounderProfile } from "../../types/profile";
import type { DecisionMeta } from "../../data/decisionMeta";

export function DecisionDetailSidebar({ profile, candidate, meta }: { profile: FounderProfile; candidate: CandidateDetail; meta: DecisionMeta }) {
  return (
    <aside className="panel overflow-hidden rounded-lg lg:sticky lg:top-5">
      <div className="h-16 bg-gradient-to-r from-[#dfeafa] via-[#e8eef9] to-[#e8f3ef]" />
      <div className="px-5 pb-5">
        <CandidateAvatar name={candidate.display_name} avatarUrl={candidate.avatar_url} className="-mt-9 mb-4 h-[72px] w-[72px] rounded-lg border-4 border-white bg-accent text-xl font-bold text-white shadow-sm" />
        <h1 className="text-[1.35rem] font-bold leading-tight tracking-[-0.025em]">{candidate.display_name ?? "Unknown founder"}</h1>
        <p className="mt-1 text-xs font-semibold text-ink-2">{profile.role}</p>
        <p className="text-xs text-muted">{profile.company}</p>

        <div className="mt-4 space-y-2.5 rounded-md bg-surface-2/75 p-3.5 text-xs leading-5 text-muted">
          <SidebarRow icon={MapPin} value={profile.location} />
          <SidebarRow icon={Building2} value={`${profile.stage} · ${profile.sector}`} />
          <SidebarRow icon={Mail} value={candidate.email ?? "Email not provided"} />
          <SidebarRow icon={Target} value={`Origin: ${candidate.origin}`} />
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2">
          <SmallMetric label="Thesis fit" value={`${profile.thesisFit}%`} />
          <SmallMetric label="Coverage" value={`${profile.coverageScore == null ? "Not scored" : `${profile.coverageScore}%`}`} />
        </div>

        <div className={`mt-4 rounded-md p-3 ${meta.slaAlert ? "bg-[#fff1df]" : "bg-surface-2"}`} role="status" aria-label={`Decision SLA status: ${meta.slaStatus}`}>
          <div className="data-label">Decision clock</div>
          <div className="mt-2 flex items-center justify-between gap-3 text-xs"><span className="text-muted">Status</span><span className={`font-bold ${meta.slaAlert ? "text-danger" : "text-ink"}`}>{formatSlaStatus(meta.slaStatus)}</span></div>
          <div className="mt-1.5 flex items-center justify-between gap-3 text-xs"><span className="text-muted">Stage</span><span className="font-bold">{meta.slaStage ?? "Not started"}</span></div>
          <div className="mt-1.5 flex items-center justify-between gap-3 text-xs"><span className="text-muted">Owner</span><span className="font-bold">{meta.slaOwner}</span></div>
        </div>

        <div className="mt-4 flex flex-wrap gap-1.5">
          {profile.tags.slice(0, 5).map((tag) => <span key={tag} className="rounded bg-surface-2 px-2 py-1 text-[10px] font-semibold text-muted">{tag}</span>)}
        </div>

        {safeExternalUrl(candidate.profile?.deck_url) && (
          <SafeLink href={safeExternalUrl(candidate.profile?.deck_url)} className="mt-5 flex w-full items-center justify-between rounded-md bg-[#e7eef9] px-3 py-2.5 text-xs font-bold text-[#5074a8] transition-all hover:-translate-y-0.5 hover:shadow-md">
            <span className="flex min-w-0 items-center gap-2"><FileText className="h-3.5 w-3.5 shrink-0" /><span className="truncate">{candidate.profile?.deck_stage ?? "Open pitch deck"}</span></span>
            <ExternalLink className="h-3.5 w-3.5 shrink-0" />
          </SafeLink>
        )}

        <Link to={`/founders/${candidate.id}`} className="mt-5 flex w-full items-center justify-center rounded-md bg-white/75 py-2.5 text-xs font-bold text-ink-2 shadow-sm transition-all hover:-translate-y-0.5 hover:text-accent hover:shadow-md">Open full founder profile</Link>

        <div className="mt-5 rounded-md bg-surface-2 p-3">
          <div className="data-label">Round context</div>
          <div className="mt-2 flex items-center justify-between text-xs"><span className="text-muted">Ask</span><span className="font-bold">{meta.ask}</span></div>
          <div className="mt-1.5 flex items-center justify-between text-xs"><span className="text-muted">Target ownership</span><span className="font-bold">{meta.targetOwnership}</span></div>
          <div className="mt-1.5 flex items-center justify-between text-xs"><span className="text-muted">Lead status</span><span className="font-bold">{meta.lead}</span></div>
        </div>
      </div>
    </aside>
  );
}

function SidebarRow({ icon: Icon, value }: { icon: React.ElementType; value: string }) {
  return <div className="flex items-start gap-2"><Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-2" /><span className="break-all">{value}</span></div>;
}

function SmallMetric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md bg-surface-2 p-3"><div className="numeric text-lg font-bold leading-none">{value}</div><div className="mt-1 text-[10px] text-muted">{label}</div></div>;
}

function formatSlaStatus(status: DecisionMeta["slaStatus"]): string {
  return status.replaceAll("_", " ");
}
