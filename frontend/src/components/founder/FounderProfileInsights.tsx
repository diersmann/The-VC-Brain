import { CalendarDays, CheckCircle2, CircleAlert, GitBranch, History, ShieldCheck } from "lucide-react";
import type { FounderProfile } from "../../types/profile";

export function FounderProfileInsights({ profile }: { profile: FounderProfile }) {
  return <>
    <section className="panel mb-5 rounded-lg p-5" aria-labelledby="profile-context-title">
      <div className="eyebrow mb-2">Profile context</div>
      <h2 id="profile-context-title" className="text-base font-bold">What the current evidence says</h2>
      <p className="mt-2 max-w-4xl text-sm leading-6 text-ink-2">{profile.summary}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted"><span className="font-bold text-accent">Signal:</span>{profile.signal}</div>
      {profile.tags.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{profile.tags.map((tag) => <span key={tag} className="rounded-full bg-surface-2 px-2.5 py-1 text-[10px] font-bold text-muted">{tag}</span>)}</div>}
    </section>

    <section className="panel mb-5 rounded-lg p-5" aria-labelledby="score-history-title">
      <div className="flex items-start justify-between gap-3"><div><div className="eyebrow mb-2">Persistent memory</div><h2 id="score-history-title" className="text-base font-bold">Founder score history</h2><p className="supporting-text mt-1">Versioned founder signals remain distinct from the opportunity assessments above.</p></div><History className="h-5 w-5 shrink-0 text-accent-muted" aria-hidden="true" /></div>
      {profile.trendHistory.length === 0 ? <div className="mt-4 rounded-md bg-surface-2 p-4 text-xs text-muted">No founder score snapshots are recorded yet.</div> : <ol className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4" aria-label="Founder score history">{profile.trendHistory.map((value, index) => <li key={`${value}-${index}`} className="rounded-md bg-surface-2/80 p-3"><div className="flex items-center justify-between text-[10px] font-bold text-muted"><span>Update {index + 1}</span><span className="numeric">{value}%</span></div><div className="mt-2 h-2 rounded-full bg-surface-3" role="progressbar" aria-label={`Founder score update ${index + 1}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={value}><div className="h-full rounded-full bg-accent" style={{ width: `${value}%` }} /></div></li>)}</ol>}
    </section>

    <div className="mb-5 grid gap-5 lg:grid-cols-2">
      <section className="panel rounded-lg p-5" aria-labelledby="evidence-timeline-title">
        <div className="eyebrow mb-2">Evidence timeline</div>
        <h2 id="evidence-timeline-title" className="text-base font-bold">What was observed, and when</h2>
        {profile.events.length === 0 ? <div className="mt-4 rounded-md bg-surface-2 p-4 text-xs text-muted">No dated source observations are available.</div> : <ol className="mt-4 space-y-4" aria-label="Evidence timeline">{profile.events.map((event, index) => <li key={`${event.date}-${event.title}-${index}`} className="flex gap-3"><div className="flex flex-col items-center" aria-hidden="true"><span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent-soft text-accent"><CalendarDays className="h-3.5 w-3.5" /></span>{index < profile.events.length - 1 && <span className="mt-1 h-full w-px bg-line" />}</div><div className="min-w-0 flex-1 pb-1"><div className="flex flex-wrap items-start justify-between gap-2"><h3 className="text-xs font-bold text-ink-2">{event.title}</h3><span className="numeric rounded bg-surface-2 px-2 py-1 text-[10px] font-bold text-muted">{event.trust}% trust</span></div><p className="mt-1 text-xs leading-5 text-muted">{event.body}</p><div className="mt-1 text-[10px] font-semibold uppercase tracking-wider text-muted-2">{event.type} · {event.date}</div></div></li>)}</ol>}
      </section>

      <section className="panel rounded-lg p-5" aria-labelledby="coverage-gaps-title">
        <div className="eyebrow mb-2">Coverage & gaps</div>
        <h2 id="coverage-gaps-title" className="text-base font-bold">Where the evidence is strong or thin</h2>
        <div className="mt-4 space-y-3" role="list" aria-label="Evidence coverage">{profile.coverage.map((item) => <div key={item.label} role="listitem"><div className="mb-1 flex items-center justify-between gap-3 text-xs font-semibold"><span>{item.label}</span><span className="numeric text-muted">{item.value}%</span></div><div className="h-2 rounded-full bg-surface-3" role="progressbar" aria-label={`${item.label} coverage`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={item.value}><div className="h-full rounded-full bg-[#6f8db7]" style={{ width: `${item.value}%` }} /></div></div>)}</div>
        <div className="mt-5 rounded-md bg-[#fff1df] p-3.5"><div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-warn"><CircleAlert className="h-3.5 w-3.5" aria-hidden="true" />Open questions</div>{profile.gaps.length > 0 ? <ul className="mt-2 space-y-1.5 text-xs leading-5 text-ink-2">{profile.gaps.map((gap) => <li key={gap}>· {gap}</li>)}</ul> : <p className="mt-2 text-xs text-ink-2">No open evidence gaps are recorded.</p>}</div>
      </section>
    </div>

    <section className="panel rounded-lg p-5" aria-labelledby="relationships-title">
      <div className="flex items-start justify-between gap-3"><div><div className="eyebrow mb-2">Network context</div><h2 id="relationships-title" className="text-base font-bold">Projects & relationships</h2><p className="supporting-text mt-1">Relationships are sourcing context; they do not change founder merit.</p></div><GitBranch className="h-5 w-5 shrink-0 text-accent-muted" aria-hidden="true" /></div>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div><div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-muted">Affiliations</div>{profile.affiliations.length > 0 ? <ul className="space-y-2">{profile.affiliations.map((affiliation) => <li key={`${affiliation.kind}-${affiliation.name}`} className="rounded-md bg-surface-2/80 p-3"><div className="text-xs font-bold">{affiliation.name}</div><div className="mt-1 text-[11px] text-muted">{affiliation.role} · {affiliation.meta}</div></li>)}</ul> : <p className="rounded-md bg-surface-2 p-3 text-xs text-muted">No project or company affiliations are linked.</p>}</div>
        <div><div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-muted">Typed relationships</div>{profile.relations.length > 0 ? <ul className="space-y-2">{profile.relations.map((relation) => <li key={`${relation.kind}-${relation.label}-${relation.sub}`} className="flex items-start justify-between gap-3 rounded-md bg-surface-2/80 p-3"><div><div className="text-xs font-bold">{relation.label}</div><div className="mt-1 text-[11px] text-muted">{relation.sub}</div></div><span className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-1 text-[10px] font-bold ${relation.verified ? "bg-[#e4f2ed] text-success" : "bg-[#fff1df] text-warn"}`}>{relation.verified ? <ShieldCheck className="h-3 w-3" aria-hidden="true" /> : <CircleAlert className="h-3 w-3" aria-hidden="true" />}{relation.verified ? "Verified" : "Needs verification"}</span></li>)}</ul> : <p className="rounded-md bg-surface-2 p-3 text-xs text-muted">No typed relationships are linked.</p>}</div>
      </div>
      <p className="mt-4 flex items-center gap-2 text-[10px] text-muted"><CheckCircle2 className="h-3.5 w-3.5 text-success" aria-hidden="true" />Verified links are supported by stronger evidence; unverified links remain weak sourcing context.</p>
    </section>
  </>;
}
