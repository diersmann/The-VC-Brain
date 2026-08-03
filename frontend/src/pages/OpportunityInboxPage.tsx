import { useMemo } from "react";
import type { ReactNode } from "react";
import { AlertTriangle, ArrowRight, CheckCircle2, Inbox, Search, ShieldAlert } from "lucide-react";
import { Link, useSearchParams } from "react-router";
import { useCandidates } from "../api/candidates";
import { CandidateAvatar } from "../components/common/CandidateAvatar";
import { formatDate, formatPredicate } from "../data/candidateProfile";
import type { Candidate } from "../types/candidate";

type InboxView = "all" | "attention" | "inbound" | "outbound" | "decision";

const viewLabels: Record<InboxView, string> = {
  all: "All opportunities",
  attention: "Needs attention",
  inbound: "Inbound applications",
  outbound: "Outbound discoveries",
  decision: "Decision ready",
};

export function OpportunityInboxPage() {
  const { data = [], isLoading, error } = useCandidates();
  const [searchParams, setSearchParams] = useSearchParams();
  const view = parseView(searchParams.get("view"));
  const query = searchParams.get("q") ?? "";
  const visible = useMemo(() => filterCandidates(data, view, query), [data, query, view]);

  const updateSearch = (key: "q" | "view", value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next, { replace: true });
  };

  return (
    <div className="mx-auto max-w-[1160px] pb-10">
      <header className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><div className="eyebrow mb-2">Opportunity workflow</div><h1 className="page-title">Unified inbox</h1><p className="page-description">One view of inbound applications and outbound opportunities, with current stage, SLA risk, and the next honest action.</p></div>
        <div className="flex items-center gap-2 rounded-md bg-white/70 px-3 py-2 text-xs font-semibold text-muted shadow-sm"><Inbox className="h-4 w-4 text-accent" />{visible.length} visible</div>
      </header>

      <section className="mb-5 grid gap-3 sm:grid-cols-3">
        <Metric label="All opportunities" value={data.length} icon={<Inbox className="h-4 w-4" />} />
        <Metric label="Needs attention" value={data.filter((candidate) => needsAttention(candidate)).length} icon={<AlertTriangle className="h-4 w-4" />} />
        <Metric label="Decision ready" value={data.filter((candidate) => candidate.lifecycle_stage === "memo_ready").length} icon={<CheckCircle2 className="h-4 w-4" />} />
      </section>

      <section className="panel rounded-lg p-3">
        <div className="flex flex-col gap-3 border-b border-line pb-3 md:flex-row md:items-center md:justify-between">
          <label className="relative block max-w-md flex-1"><span className="sr-only">Search opportunities</span><Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-2" /><input value={query} onChange={(event) => updateSearch("q", event.target.value)} placeholder="Search founder, company, source…" className="w-full rounded-md bg-surface-2 py-2.5 pl-9 pr-3 text-xs outline-none focus:ring-2 focus:ring-accent/20" /></label>
          <label className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-muted-2"><span>Saved view</span><select value={view} onChange={(event) => updateSearch("view", event.target.value)} className="rounded-md bg-white px-3 py-2 text-xs font-semibold normal-case tracking-normal text-ink shadow-sm outline-none focus:ring-2 focus:ring-accent/20">{Object.entries(viewLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        </div>
        {isLoading && <div className="py-14 text-center text-sm text-muted">Loading opportunities…</div>}
        {error && <div role="alert" className="py-14 text-center text-sm text-danger">Unable to load the unified inbox.</div>}
        {!isLoading && !error && visible.length === 0 && <div className="py-14 text-center"><div className="text-sm font-bold">No opportunities in this view</div><p className="mt-2 text-xs text-muted">Try another saved view or search term. Missing evidence is not a negative score.</p></div>}
        <div className="divide-y divide-line">
          {visible.map((candidate) => <InboxRow key={candidate.id} candidate={candidate} />)}
        </div>
      </section>
    </div>
  );
}

function InboxRow({ candidate }: { candidate: Candidate }) {
  const stage = candidate.lifecycle_stage ?? "not_started";
  const sla = candidate.sla;
  const risk = sla?.alert_level ?? "none";
  const blockers = blockersFor(candidate);
  return (
    <Link to={`/founders/${candidate.id}`} className="grid gap-4 px-3 py-4 transition hover:bg-white/65 lg:grid-cols-[1.35fr_.8fr_.8fr_1.15fr_auto] lg:items-center">
      <div className="flex min-w-0 items-center gap-3"><CandidateAvatar name={candidate.display_name} avatarUrl={candidate.avatar_url} className="h-10 w-10 shrink-0 rounded-md bg-accent-soft text-xs font-bold text-accent" /><div className="min-w-0"><div className="truncate text-sm font-bold">{candidate.display_name ?? candidate.stable_id}</div><div className="mt-1 truncate text-[11px] text-muted">{candidate.profile?.company ?? "Company not disclosed"} · {sourceLabel(candidate)}</div></div></div>
      <div><div className="data-label">Stage</div><div className="mt-1 text-xs font-semibold text-ink-2">{formatPredicate(stage)}</div><div className="mt-1 text-[10px] text-muted">Added {formatDate(candidate.created_at)}</div></div>
      <div><div className="data-label">SLA / owner</div><div className={`mt-1 flex items-center gap-1 text-xs font-semibold ${risk === "breach" ? "text-danger" : risk === "warning" ? "text-warn" : "text-ink-2"}`}>{risk !== "none" && <ShieldAlert className="h-3.5 w-3.5" />}{sla?.status ? formatPredicate(sla.status) : "Not started"}</div><div className="mt-1 text-[10px] text-muted">{sla?.owner ?? "Owner unavailable"}</div></div>
      <div><div className="data-label">Next action</div><div className="mt-1 text-xs font-semibold text-ink-2">{nextAction(stage)}</div><div className="mt-1 truncate text-[10px] text-muted">{blockers.length ? `Blocker: ${blockers[0]}` : "No recorded blocker"}</div></div>
      <ArrowRight className="h-4 w-4 self-center text-accent" />
    </Link>
  );
}

function filterCandidates(candidates: Candidate[], view: InboxView, query: string): Candidate[] {
  const normalized = query.trim().toLowerCase();
  return candidates.filter((candidate) => {
    const matchesView = view === "all" || (view === "attention" ? needsAttention(candidate) : view === "decision" ? candidate.lifecycle_stage === "memo_ready" : candidate.origin === view);
    const haystack = [candidate.display_name, candidate.stable_id, candidate.email, candidate.origin, candidate.profile?.company, ...(candidate.profile?.source_types ?? [])].filter(Boolean).join(" ").toLowerCase();
    return matchesView && (!normalized || haystack.includes(normalized));
  });
}

function blockersFor(candidate: Candidate): string[] {
  const blockers: string[] = [];
  if (!candidate.scores?.founder && candidate.scores?.founder !== 0) blockers.push("Founder Score pending");
  if (!candidate.thesis_match && candidate.lifecycle_stage !== "discovered") blockers.push("Thesis match pending");
  if (candidate.sla?.alert) blockers.push("SLA at risk");
  return blockers;
}

function needsAttention(candidate: Candidate): boolean { return Boolean(candidate.sla?.alert || blockersFor(candidate).length); }
function nextAction(stage: string): string { return ({ discovered: "Collect evidence", interesting: "Activate investigation", investigating: "Review investigation", contacted: "Await application", received: "Triage submission", triage: "Complete screening", screening: "Run opportunity research", diligence: "Generate memo", memo_ready: "Record decision", hold: "Revisit hold", approved: "Monitor outcome", closed: "No action" } as Record<string, string>)[stage] ?? "Review opportunity"; }
function sourceLabel(candidate: Candidate): string { return [candidate.origin ? formatPredicate(candidate.origin) : "Source unavailable", ...(candidate.profile?.source_types ?? []).map(formatPredicate)].join(" · "); }
function parseView(value: string | null): InboxView { return value && value in viewLabels ? value as InboxView : "all"; }
function Metric({ label, value, icon }: { label: string; value: number; icon: ReactNode }) { return <div className="panel flex items-center gap-3 rounded-lg p-4"><span className="flex h-8 w-8 items-center justify-center rounded-md bg-accent-soft text-accent">{icon}</span><div><div className="numeric text-xl font-bold">{value}</div><div className="text-[10px] font-semibold uppercase tracking-wider text-muted">{label}</div></div></div>; }
