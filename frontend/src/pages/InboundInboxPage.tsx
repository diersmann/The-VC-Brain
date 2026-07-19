import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { ArrowRight, FileText, Filter, Inbox, Search, ShieldCheck, Sparkles } from "lucide-react";
import { useCandidates } from "../api/candidates";
import { CandidateAvatar } from "../components/common/CandidateAvatar";
import { formatDate, formatPredicate, percentage } from "../data/candidateProfile";

export function InboundInboxPage() {
  const navigate = useNavigate();
  const { data = [], isLoading, error } = useCandidates();
  const [query, setQuery] = useState("");
  const inbound = useMemo(() => data.filter((candidate) => {
    if (candidate.origin !== "inbound") return false;
    return !query || (candidate.display_name ?? candidate.stable_id).toLowerCase().includes(query.toLowerCase());
  }), [data, query]);
  const parsed = inbound.filter((candidate) => candidate.scores).length;
  const needsAttention = inbound.length - parsed;

  return (
    <div className="mx-auto max-w-[1160px] pb-10">
      <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><div className="eyebrow mb-2">Founder applications</div><h1 className="text-3xl font-bold tracking-tight">Inbound inbox</h1><p className="mt-2 text-sm text-muted">Applications stored in the live database with extracted scores.</p></div>
        <div className="flex gap-2"><button className="flex items-center gap-2 rounded-md bg-white/75 px-3 py-2 text-xs font-semibold shadow-sm"><Filter className="h-3.5 w-3.5" />Filter</button><button className="rounded-md bg-accent px-4 py-2 text-xs font-semibold text-white">Copy application link</button></div>
      </div>

      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <Stat icon={Inbox} value={String(inbound.length)} label="Inbound records" tone="purple" />
        <Stat icon={Sparkles} value={String(parsed)} label="Scored records" tone="blue" />
        <Stat icon={ShieldCheck} value={String(needsAttention)} label="Need assessment" tone="amber" />
      </div>

      <section className="panel space-y-1 rounded-lg p-2">
        <div className="flex items-center gap-3 rounded-md bg-gradient-to-r from-[#edf3fb] to-transparent px-3 py-3"><div className="relative max-w-sm flex-1"><Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-2" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search applications..." className="w-full rounded-md bg-white/70 py-2 pl-9 pr-3 text-xs shadow-inner shadow-slate-200/60 outline-none focus:bg-white" /></div><span className="text-[10px] text-muted">Live database records</span></div>
        {isLoading && <div className="py-12 text-center text-xs text-muted">Loading inbound records…</div>}
        {error && <div className="py-12 text-center text-xs text-danger">Unable to load inbound records.</div>}
        {!isLoading && !error && inbound.length === 0 && <div className="py-14 text-center"><div className="text-sm font-bold">No inbound applications in the database</div><p className="mt-2 text-xs text-muted">Public discoveries remain available in Discover.</p></div>}
        <div className="space-y-1">
          {inbound.map((candidate) => {
            const source = Object.keys(candidate.handles ?? {})[0] ?? "inbound";
            return (
              <button key={candidate.id} onClick={() => navigate(`/founders/${candidate.id}`)} className="grid w-full items-center gap-4 rounded-md px-3 py-3.5 text-left transition-colors hover:bg-white/65 lg:grid-cols-[1.35fr_.8fr_.7fr_1.1fr_auto]">
                <div className="flex items-center gap-3"><CandidateAvatar name={candidate.display_name} avatarUrl={candidate.avatar_url} className="h-10 w-10 rounded-md bg-[#eee8f8] text-xs font-bold text-[#7656a5]" /><div><div className="text-xs font-bold">{candidate.display_name ?? candidate.stable_id}</div><div className="text-[10px] text-muted">{formatPredicate(source)}</div></div></div>
                <Cell label="Received" value={formatDate(candidate.created_at)} />
                <div><div className="text-[9px] font-bold uppercase tracking-wider text-muted-2">Thesis match</div><div className="mt-1 flex items-center gap-1 text-xs font-bold text-success"><ShieldCheck className="h-3 w-3" />{candidate.scores?.thesis_fit == null ? "Pending" : `${percentage(candidate.scores.thesis_fit)}%`}</div></div>
                <div><div className="text-[9px] font-bold uppercase tracking-wider text-muted-2">Review</div><div className="mt-1 flex items-center gap-1 text-[11px] font-semibold"><Sparkles className="h-3 w-3 text-warn" />{candidate.scores ? "Score available" : "Needs assessment"}</div><div className="mt-1 text-[9px] text-muted">Consent: {formatPredicate(candidate.consent_state)}</div></div>
                <ArrowRight className="h-4 w-4 text-accent" />
              </button>
            );
          })}
        </div>
      </section>
      <div className="mt-4 flex items-center gap-2 text-[10px] text-muted"><FileText className="h-3.5 w-3.5 text-accent" />Only records whose opportunity origin is inbound appear here.</div>
    </div>
  );
}

function Stat({ icon: Icon, value, label, tone }: { icon: React.ElementType; value: string; label: string; tone: "purple" | "blue" | "amber" }) { const colors = { purple: "bg-[#eee8f8] text-[#7656a5]", blue: "bg-[#e7eef9] text-[#5074a8]", amber: "bg-[#fff1df] text-[#a96e2d]" }; return <div className="panel flex items-center gap-3 rounded-lg p-4"><span className={`flex h-9 w-9 items-center justify-center rounded-md ${colors[tone]}`}><Icon className="h-4 w-4" /></span><div><div className="text-lg font-bold">{value}</div><div className="text-[10px] text-muted">{label}</div></div></div>; }
function Cell({ label, value }: { label: string; value: string }) { return <div><div className="text-[9px] font-bold uppercase tracking-wider text-muted-2">{label}</div><div className="mt-1 text-[11px] font-semibold">{value}</div></div>; }
