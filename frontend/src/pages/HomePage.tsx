import { useNavigate } from "react-router";
import { AlertTriangle, ArrowRight, CheckCircle2, Clock3, Compass, Inbox, Scale, Target } from "lucide-react";
import { useCandidates } from "../api/candidates";
import { CandidateAvatar } from "../components/common/CandidateAvatar";
import { formatDate, formatPredicate, percentage } from "../data/candidateProfile";

export function HomePage() {
  const navigate = useNavigate();
  const { data = [] } = useCandidates();
  const inbound = data.filter((candidate) => candidate.origin === "inbound");
  const outbound = data.filter((candidate) => candidate.origin === "outbound");
  const scored = data.filter((candidate) => candidate.scores);
  const highSignal = data.filter((candidate) => (candidate.scores?.thesis_fit ?? candidate.scores?.raw?.composite ?? 0) >= 0.45);
  const priorities = [...data].sort((a, b) => score(b) - score(a)).slice(0, 4);

  return (
    <div className="mx-auto max-w-[1220px] pb-10">
      <section className="mb-7 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div><div className="eyebrow mb-2">Investment workspace</div><h1 className="text-3xl font-bold tracking-tight">Good morning, Sophie</h1><p className="mt-2 text-sm text-muted">Live sourcing and decision data from the VC Brain database.</p></div>
        <button onClick={() => navigate("/thesis")} className="flex w-fit items-center gap-3 rounded-md bg-white/75 px-4 py-2.5 shadow-[0_8px_24px_rgba(70,91,120,.08)] backdrop-blur-xl"><span className="h-2 w-2 rounded-full bg-success" /><div className="text-left"><div className="text-xs font-bold">Berlin Deep Tech</div><div className="text-[10px] text-muted">Active thesis</div></div><ArrowRight className="h-3.5 w-3.5 text-muted" /></button>
      </section>

      <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric icon={Inbox} label="Inbound records" value={String(inbound.length)} hint="Live database" color="purple" />
        <Metric icon={Compass} label="Public discoveries" value={String(outbound.length)} hint={`${highSignal.length} high signal`} color="green" />
        <Metric icon={Clock3} label="Awaiting score" value={String(data.length - scored.length)} hint="Need assessment" color="amber" />
        <Metric icon={CheckCircle2} label="Scored profiles" value={String(scored.length)} hint="Versioned scores" color="blue" />
      </div>

      <div className="mb-6 grid gap-4 lg:grid-cols-3">
        <Action icon={Inbox} color="purple" title="Review inbound" text={`${inbound.length} database records are marked as inbound.`} button="Open inbox" onClick={() => navigate("/inbound")} />
        <Action icon={Compass} color="green" title="Discover outbound" text={`${outbound.length} people were collected from public activity signals.`} button="Open discover" onClick={() => navigate("/sourcing")} />
        <Action icon={Scale} color="amber" title="Make decisions" text={`${data.length} candidates are available for human review.`} button="Open queue" onClick={() => navigate("/decisions")} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
        <section className="panel space-y-1 rounded-lg p-2">
          <div className="flex items-center justify-between rounded-md bg-gradient-to-r from-[#edf3fb] to-transparent px-3 py-3"><div><h2 className="text-sm font-bold">Priority candidates</h2><p className="text-[11px] text-muted">Ordered by recorded thesis or discovery signal</p></div><button onClick={() => navigate("/decisions")} className="text-xs font-bold text-accent">View all</button></div>
          {priorities.length === 0 && <div className="px-3 py-10 text-center text-xs text-muted">No live candidates yet.</div>}
          {priorities.map((candidate, index) => {
            const source = Object.keys(candidate.handles ?? {})[0] ?? candidate.origin ?? "database";
            return (
              <button key={candidate.id} onClick={() => navigate(`/decisions/${candidate.id}`)} className="grid w-full items-center gap-3 rounded-md px-3 py-3.5 text-left transition-colors hover:bg-white/65 sm:grid-cols-[1.2fr_.8fr_1.2fr_auto]">
                <div className="flex items-center gap-3"><CandidateAvatar name={candidate.display_name} avatarUrl={candidate.avatar_url} className={`h-9 w-9 rounded-md text-xs font-bold ${tone(["amber", "blue", "purple", "green"][index % 4])}`} /><div><div className="text-xs font-bold">{candidate.display_name ?? candidate.stable_id}</div><div className="text-[10px] text-muted">{formatPredicate(source)} · {candidate.origin ?? "unclassified"}</div></div></div>
                <Cell label="Stage" value={candidate.scores ? "Scored" : "Discovery"} />
                <div><div className="text-[9px] font-bold uppercase tracking-wider text-muted-2">Next action</div><div className="mt-1 flex items-center gap-1 text-[11px] font-semibold"><AlertTriangle className="h-3 w-3 text-warn" />{candidate.scores ? "Review evidence" : "Complete scoring"}</div></div>
                <span className="text-[9px] text-muted">{formatDate(candidate.created_at)}</span>
              </button>
            );
          })}
        </section>

        <section className="panel rounded-lg p-5"><div className="mb-5 flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-md bg-accent-soft text-accent"><Target className="h-4 w-4" /></span><div><h2 className="text-sm font-bold">Active thesis</h2><p className="text-[11px] text-muted">Berlin Deep Tech</p></div></div>{["AI Infrastructure", "Pre-seed / Seed", "DACH & Europe", "€250k – €500k"].map((item) => <div key={item} className="mb-2 flex items-center gap-2 rounded-md bg-white/60 px-3 py-2.5 text-[11px] font-semibold shadow-sm"><CheckCircle2 className="h-3.5 w-3.5 text-success" />{item}</div>)}<button onClick={() => navigate("/thesis")} className="mt-4 flex items-center gap-1 text-xs font-bold text-accent">Edit thesis <ArrowRight className="h-3.5 w-3.5" /></button></section>
      </div>
    </div>
  );
}

function score(candidate: { scores: { thesis_fit: number | null; raw?: Record<string, number> | null } | null }): number {
  return percentage(candidate.scores?.thesis_fit ?? candidate.scores?.raw?.composite);
}
function tone(color: string) { return color === "purple" ? "bg-[#eee8f8] text-[#7656a5]" : color === "green" ? "bg-[#e4f2ed] text-[#347c67]" : color === "amber" ? "bg-[#fff1df] text-[#a96e2d]" : "bg-[#e7eef9] text-[#5074a8]"; }
function Metric({ icon: Icon, label, value, hint, color }: { icon: React.ElementType; label: string; value: string; hint: string; color: string }) { return <div className="panel flex items-center gap-3 rounded-lg p-4"><span className={`flex h-10 w-10 items-center justify-center rounded-md ${tone(color)}`}><Icon className="h-4 w-4" /></span><div><div className="text-lg font-bold">{value}</div><div className="text-[10px] font-semibold text-ink-2">{label}</div></div><span className="ml-auto self-end text-[9px] text-muted">{hint}</span></div>; }
function Action({ icon: Icon, color, title, text, button, onClick }: { icon: React.ElementType; color: string; title: string; text: string; button: string; onClick: () => void }) { return <button onClick={onClick} className="panel group rounded-lg p-5 text-left transition hover:-translate-y-0.5"><span className={`flex h-10 w-10 items-center justify-center rounded-md ${tone(color)}`}><Icon className="h-5 w-5" /></span><h2 className="mt-4 text-sm font-bold">{title}</h2><p className="mt-1.5 text-[11px] leading-5 text-muted">{text}</p><span className="mt-4 flex items-center gap-1 text-xs font-bold text-accent">{button}<ArrowRight className="h-3.5 w-3.5 transition group-hover:translate-x-1" /></span></button>; }
function Cell({ label, value }: { label: string; value: string }) { return <div><div className="text-[9px] font-bold uppercase tracking-wider text-muted-2">{label}</div><div className="mt-1 text-[11px] font-semibold">{value}</div></div>; }
