import { useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { AlertTriangle, ArrowRight, ExternalLink, FileText, Inbox, Search, ShieldCheck, Sparkles, Target } from "lucide-react";
import { useInfiniteCandidateList } from "../api/candidates";
import { CandidateAvatar } from "../components/common/CandidateAvatar";
import { KeyMetricCard } from "../components/common/KeyMetricCard";
import { SafeLink } from "../components/common/SafeLink";
import { formatDate, formatPredicate } from "../data/candidateProfile";
import { safeExternalUrl } from "../data/candidateLinks";
import { scoreViewModel } from "../data/displayMetrics";
import { hasDecisionScore, isThesisAligned, ratioPercent } from "../data/portfolioMetrics";
import type { Candidate } from "../types/candidate";
import { DECISION_RUBRIC } from "../data/rubric";

export function InboundInboxPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get("q") ?? "";
  // Filter at the API so inbound applications are not lost behind the
  // candidates endpoint's page limit. Pages are accumulated only when the
  // reviewer explicitly asks for more records.
  const allQuery = useInfiniteCandidateList(undefined, "inbound");
  const filteredQuery = useInfiniteCandidateList(undefined, "inbound", query);
  const allData = useMemo(() => allQuery.data?.pages.flatMap((page) => page.items) ?? [], [allQuery.data]);
  const filteredData = useMemo(() => filteredQuery.data?.pages.flatMap((page) => page.items) ?? [], [filteredQuery.data]);
  const filteredLegacy = filteredQuery.data?.pages.some((page) => page.legacy) ?? false;
  const allPage = allQuery.data?.pages[0];
  const filteredPage = filteredQuery.data?.pages[0];
  const totalCount = allPage?.total_count ?? allData.length;
  const filteredTotalCount = filteredPage?.total_count ?? filteredData.length;
  const activeQuery = query.trim() ? filteredQuery : allQuery;
  const isLoading = allQuery.isLoading || activeQuery.isLoading;
  const error = allQuery.error || activeQuery.error;
  const inboundRecords = useMemo(() => allData.filter((candidate) => candidate.origin === "inbound"), [allData]);
  const filteredInboundRecords = useMemo(() => filteredData.filter((candidate) => candidate.origin === "inbound"), [filteredData]);
  const inbound = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return inboundRecords;
    // v1 responses have already applied search across observations,
    // predicates, and source URIs. Only legacy bare-array responses need the
    // DTO-level fallback filter, otherwise valid evidence-only matches would
    // be silently removed here.
    if (!filteredLegacy) return filteredInboundRecords;
    return filteredInboundRecords.filter((candidate) => searchableCandidateText(candidate).includes(normalizedQuery));
  }, [filteredInboundRecords, filteredLegacy, inboundRecords, query]);
  const thesisAligned = inboundRecords.filter(isThesisAligned).length;
  const needsAttention = inboundRecords.filter((candidate) => !hasDecisionScore(candidate)).length;
  const setQuery = (value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value.trim()) next.set("q", value);
    else next.delete("q");
    setSearchParams(next, { replace: true });
  };

  return (
    <div className="mx-auto max-w-[1160px] pb-10">
      <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><div className="eyebrow mb-2">Founder applications</div><h1 className="page-title">Inbound inbox</h1><p className="page-description">Applications stored in the live database with extracted scores.</p></div>
      </div>

      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <KeyMetricCard icon={Inbox} label="Applications" value={totalCount} detail="Founder-submitted opportunities in the live database" progress={100} progressLabel={`${allData.length} loaded of ${totalCount} total`} tone="purple" />
        <KeyMetricCard icon={Target} label="Thesis aligned" value={thesisAligned} detail={`Loaded-page applications clearing the ${DECISION_RUBRIC.thesisAlignment}% strategy-fit threshold`} progress={ratioPercent(thesisAligned, allData.length)} progressLabel={`${thesisAligned} of ${allData.length} loaded`} tone="green" />
        <KeyMetricCard icon={AlertTriangle} label="Needs assessment" value={needsAttention} detail="Loaded-page applications without a usable decision score" progress={ratioPercent(needsAttention, allData.length)} progressLabel={`${needsAttention} of ${allData.length} loaded`} tone="amber" />
      </div>

      <section className="panel space-y-1 rounded-lg p-2">
          <div className="flex flex-col gap-3 rounded-md bg-gradient-to-r from-[#edf3fb] to-transparent px-3 py-3 sm:flex-row sm:items-center"><div className="relative max-w-sm flex-1"><Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-2" /><label htmlFor="inbound-search" className="sr-only">Search inbound applications</label><input id="inbound-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search name, company, email, source or deck..." className="w-full rounded-md bg-white/70 py-2.5 pl-9 pr-3 text-sm shadow-inner shadow-slate-200/60 outline-none focus:bg-white" /></div><div className="flex items-center justify-between gap-3 text-[11px] text-muted"><span aria-live="polite">Showing {inbound.length} of {filteredTotalCount} inbound applications</span>{query.trim() && <button type="button" onClick={() => setQuery("")} className="font-bold text-accent hover:underline">Clear search</button>}</div></div>
        <div className="flex flex-wrap items-center gap-2 px-3 pt-2 text-[10px] text-muted"><span className="rounded-full bg-[#eee8f8] px-2.5 py-1 font-bold text-[#7656a5]">Origin: inbound</span>{query.trim() && <span className="rounded-full bg-surface-2 px-2.5 py-1">Search: “{query.trim()}”</span>}</div>
        {isLoading && <div className="py-12 text-center text-xs text-muted">Loading inbound records…</div>}
        {error && <div className="py-12 text-center text-xs text-danger">Unable to load inbound records.</div>}
        {!isLoading && !error && inboundRecords.length === 0 && <div className="py-14 text-center"><div className="text-sm font-bold">No inbound applications in the database</div><p className="mt-2 text-xs text-muted">Public discoveries remain available in Discover.</p></div>}
        {!isLoading && !error && inboundRecords.length > 0 && inbound.length === 0 && <div className="py-14 text-center"><div className="text-sm font-bold">No applications match “{query.trim()}”</div><p className="mt-2 text-xs text-muted">Try a different name, company, email, source or deck term.</p><button type="button" onClick={() => setQuery("")} className="mt-3 text-xs font-bold text-accent hover:underline">Clear search</button></div>}
        <div className="space-y-1">
          {inbound.map((candidate) => {
            const source = Object.keys(candidate.handles ?? {})[0] ?? "inbound";
            return (
              <div key={candidate.id} className="grid w-full items-center gap-4 rounded-md px-3 py-3.5 text-left transition-colors hover:bg-white/65 lg:grid-cols-[1.35fr_.8fr_.7fr_1.1fr_auto]">
                <div className="flex items-center gap-3"><CandidateAvatar name={candidate.display_name} avatarUrl={candidate.avatar_url} className="h-10 w-10 rounded-md bg-[#eee8f8] text-xs font-bold text-[#7656a5]" /><div><div className="text-sm font-bold leading-tight">{candidate.display_name ?? candidate.stable_id}</div><div className="mt-1 text-[11px] text-muted">{candidate.profile?.company ?? formatPredicate(source)}</div>{candidate.profile?.inbound_label && <div className="mt-1 text-[10px] font-semibold text-[#7656a5]">{candidate.profile.inbound_label}</div>}</div></div>
                <Cell label="Received" value={formatDate(candidate.created_at)} />
                <ThesisScore value={candidate.scores?.thesis_fit} />
                <div><div className="data-label">Deck</div>{safeExternalUrl(candidate.profile?.deck_url) ? <SafeLink href={safeExternalUrl(candidate.profile?.deck_url)} onClick={(event) => event.stopPropagation()} onKeyDown={(event) => event.stopPropagation()} className="mt-1.5 inline-flex items-center gap-1 text-xs font-semibold text-accent hover:underline"><FileText className="h-3.5 w-3.5" />{candidate.profile?.deck_stage ?? "Open deck"}<ExternalLink className="h-3 w-3" /></SafeLink> : <div className="mt-1.5 flex items-center gap-1 text-xs font-semibold"><Sparkles className="h-3.5 w-3.5 text-warn" />Needs assessment</div>}<div className="mt-1 max-w-[220px] truncate text-[10px] text-muted">{candidate.profile?.deck_title ?? `Consent: ${formatPredicate(candidate.consent_state)}`}</div></div>
                <button
                  type="button"
                  onClick={() => navigate(`/founders/${candidate.id}`)}
                  className="inline-flex min-h-11 items-center justify-end gap-1 px-2 text-xs font-bold text-accent hover:underline"
                  aria-label={`View founder ${candidate.display_name ?? candidate.stable_id}`}
                >
                  View founder
                  <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            );
          })}
        </div>
        {activeQuery.isFetchNextPageError && (
          <div role="alert" className="flex items-center justify-center gap-3 border-t border-danger/20 px-3 py-4 text-xs text-danger">
            <span>Unable to load more inbound applications.</span>
            <button
              type="button"
              onClick={() => void activeQuery.fetchNextPage()}
              className="font-bold underline underline-offset-2"
              aria-label="Retry loading more inbound applications"
            >
              Try again
            </button>
          </div>
        )}
        {!isLoading && !error && inbound.length > 0 && activeQuery.hasNextPage && (
          <div className="flex justify-center border-t border-slate-200/70 px-3 py-4">
            <button
              type="button"
              onClick={() => void activeQuery.fetchNextPage()}
              disabled={activeQuery.isFetchingNextPage}
              className="rounded-md border border-accent/30 bg-white px-4 py-2 text-xs font-bold text-accent shadow-sm transition-colors hover:bg-accent-soft disabled:cursor-wait disabled:opacity-60"
              aria-label={activeQuery.isFetchingNextPage ? "Loading more inbound applications" : "Load more inbound applications"}
            >
              {activeQuery.isFetchingNextPage ? "Loading more…" : `Load more applications (${Math.max(filteredTotalCount - inbound.length, 0)} remaining)`}
            </button>
          </div>
        )}
      </section>
      <div className="mt-4 flex items-center gap-2 text-[10px] text-muted"><FileText className="h-3.5 w-3.5 text-accent" />Only records whose opportunity origin is inbound appear here.</div>
    </div>
  );
}

function searchableCandidateText(candidate: Candidate): string {
  return [
    candidate.display_name,
    candidate.stable_id,
    candidate.email,
    candidate.origin,
    ...Object.entries(candidate.handles ?? {}).flat(),
    candidate.profile?.company,
    candidate.profile?.deck_title,
    candidate.profile?.deck_url,
    ...(candidate.profile?.source_types ?? []),
  ].filter(Boolean).join(" ").toLowerCase();
}

function Cell({ label, value }: { label: string; value: string }) { return <div><div className="data-label">{label}</div><div className="data-value numeric">{value}</div></div>; }
function ThesisScore({ value }: { value: number | null | undefined }) {
  const visual = scoreViewModel(value);
  return <div><div className="data-label">Thesis match</div><div className="mt-1 flex items-center gap-1 text-sm font-bold text-success"><ShieldCheck className="h-3.5 w-3.5" /><span className="numeric">{visual.percent == null ? "Pending" : visual.label}</span></div><div className="mt-2 h-1.5 w-full max-w-24 overflow-hidden rounded-full bg-surface-3" role="progressbar" aria-label="Thesis match" aria-valuemin={0} aria-valuemax={100} aria-valuenow={visual.percent ?? undefined} aria-valuetext={visual.explanation} title={visual.explanation}><div className="h-full rounded-full bg-success" style={{ width: `${visual.percent ?? 0}%` }} /></div></div>;
}
