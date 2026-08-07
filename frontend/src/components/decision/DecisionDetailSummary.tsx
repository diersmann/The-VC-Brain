import { ShieldCheck, Sparkles, Target, Users } from "lucide-react";
import { KeyMetricCard } from "../common/KeyMetricCard";
import type { DecisionMeta } from "../../data/decisionMeta";
import { claimStatusViewModel, recommendationViewModel } from "../../data/displayMetrics";
import type { FounderProfile } from "../../types/profile";

export function AiSummary({ profile, meta }: { profile: FounderProfile; meta: DecisionMeta }) {
  const recommendation = recommendationViewModel(meta.recommendation);

  return (
    <section className="panel rounded-lg p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="eyebrow mb-2 flex items-center gap-1.5"><Sparkles className="h-3.5 w-3.5" /> AI investment summary</div><h2 className="text-xl font-bold tracking-tight">{profile.company} at a glance</h2></div><div role="status" aria-label={`AI recommendation: ${meta.recommendation}`} title={recommendation.explanation} className="inline-flex items-center gap-2 rounded-md px-2.5 py-2" style={{ backgroundColor: recommendation.soft }}><span className="h-2 w-2 rounded-full" style={{ backgroundColor: recommendation.color }} /><span className="text-[10px] font-bold" style={{ color: recommendation.color }}>{meta.recommendation} · {recommendation.label}</span></div></div>
      <p className="mt-4 max-w-[900px] text-sm leading-7 text-ink-2">{meta.aiSummary}</p>
      {meta.conviction || meta.readinessBlockers.length > 0 ? <p className="mt-3 text-[10px] font-semibold uppercase tracking-[0.08em] text-muted-2">Proposal · {meta.conviction ?? "conviction not set"} conviction · {meta.readinessBlockers.length ? `${meta.readinessBlockers.length} readiness blocker${meta.readinessBlockers.length === 1 ? "" : "s"}` : "ready for review"}</p> : null}
      <div className="mt-4 flex items-center gap-2 text-[10px] font-semibold leading-4 text-muted-2"><ShieldCheck className="h-3.5 w-3.5 text-accent" /> Generated from available evidence; key claims still require human verification.</div>
    </section>
  );
}

export function DealMetrics({ profile, meta }: { profile: FounderProfile; meta: DecisionMeta }) {
  const founderAssessment = profile.assessments.find((assessment) => assessment.title === "Founder");
  return <section className="grid gap-3 sm:grid-cols-3"><KeyMetricCard icon={Target} label="Thesis match" value={profile.thesisFit} suffix="%" detail="Fit with the active fund strategy" progress={profile.thesisFit} progressLabel={meta.recommendation} tone="purple" /><KeyMetricCard icon={Users} label="Founder signal" value={profile.founderScore} suffix="/100" detail="Traits, execution history and team-building signal" progress={profile.founderScore} progressLabel={founderAssessment?.rating ?? "Assessment pending"} tone="green" /><KeyMetricCard icon={ShieldCheck} label="Evidence coverage" value={profile.coverageScore} suffix="%" detail="Breadth across identity, product, traction and market" progress={profile.coverageScore} progressLabel={`${profile.claims.length} evidence records`} tone="blue" /></section>;
}

export function ListCard({ title, eyebrow, icon: Icon, items, tone }: { title: string; eyebrow: string; icon: React.ElementType; items: string[]; tone: "amber" | "blue" }) {
  const colors = tone === "amber" ? "bg-[#fff1df] text-[#a96e2d]" : "bg-[#e7eef9] text-[#5074a8]";
  return <section className="panel rounded-lg p-5"><div className="flex items-center gap-3"><span className={`flex h-9 w-9 items-center justify-center rounded-md ${colors}`}><Icon className="h-4 w-4" /></span><div><div className="data-label">{eyebrow}</div><h2 className="mt-0.5 text-[15px] font-bold">{title}</h2></div></div><ul className="mt-4 space-y-3">{items.map((item, index) => <li key={item} className="flex gap-2.5 text-xs leading-5 text-ink-2"><span className={`numeric mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded text-[10px] font-bold ${colors}`}>{index + 1}</span>{item}</li>)}</ul></section>;
}

export function EvidenceCard({ profile }: { profile: FounderProfile }) {
  return <section className="panel rounded-lg p-5 sm:p-6"><div className="flex items-center justify-between gap-3"><div><div className="eyebrow mb-2">Evidence quality</div><h2 className="text-lg font-bold">Critical claims</h2></div><span className="numeric text-[11px] font-bold text-muted">{profile.claims.length} claims reviewed</span></div><div className="mt-4 space-y-2">{profile.claims.map((claim) => { const status = claimStatusViewModel(claim.status); return <div key={claim.claim} className="grid gap-3 rounded-md bg-surface-2/75 px-4 py-3 sm:grid-cols-[1fr_100px_120px] sm:items-center"><div className="text-xs font-semibold leading-5 text-ink-2">{claim.claim}</div><div className="text-[11px] text-muted">Trust <span className="numeric font-bold text-ink">{claim.trust}%</span></div><span title={status.explanation} className="status-pill w-fit" style={{ backgroundColor: status.soft, color: status.color }}>{status.label}</span></div>; })}</div></section>;
}
