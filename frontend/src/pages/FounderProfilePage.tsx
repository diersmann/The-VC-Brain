import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, AlertTriangle, AtSign, BrainCircuit, Building2, CheckCircle2, CircleHelp, ExternalLink, FileText, Github, Globe2, Linkedin, MapPin, RefreshCw, ShieldCheck, Sparkles, Target, UserRound } from "lucide-react";
import { fetchResearchStatus, researchCandidate, useCandidate } from "../api/candidates";
import { ApiStateNotice } from "../components/common/ApiStateNotice";
import { CandidateAvatar } from "../components/common/CandidateAvatar";
import { KeyMetricCard } from "../components/common/KeyMetricCard";
import { FounderAssessmentCard } from "../components/founder/FounderAssessmentCard";
import { FounderThesisReasons } from "../components/founder/FounderThesisReasons";
import { candidateExternalLinks, safeHttpUrl, type CandidateLinkKind } from "../data/candidateLinks";
import { buildFounderProfile } from "../data/candidateProfile";
import { displayScore } from "../data/displayMetrics";

const candidateLinkIcons: Record<CandidateLinkKind, React.ElementType> = { linkedin: Linkedin, github: Github, website: Globe2, deck: FileText, x: AtSign };

export function FounderProfilePage() {
  const { founderId } = useParams();
  const navigate = useNavigate();
  const { data: founder, isLoading, error, refetch } = useCandidate(founderId);
  const [researchState, setResearchState] = useState<"idle" | "queued" | "error">("idle");
  const researchStatus = useQuery({ queryKey: ["research-status", founderId], queryFn: ({ signal }) => fetchResearchStatus(founderId!, signal), enabled: Boolean(founderId), refetchInterval: researchState === "queued" ? 2_000 : false });

  useEffect(() => {
    if (researchStatus.data?.status === "completed") {
      setResearchState("idle");
      void refetch();
    }
  }, [researchStatus.data?.status, refetch]);

  if (isLoading && !founder) return <div className="py-20 text-center text-sm text-muted">Loading source evidence…</div>;
  if (error && !founder) return <div className="mx-auto max-w-[680px] py-20"><ApiStateNotice error={error} onRetry={() => void refetch()} label="founder evidence" /><button onClick={() => navigate("/sourcing")} className="mt-4 block text-xs font-bold text-accent">Back to discover</button></div>;
  if (!founder) return <div className="py-20 text-center"><div className="text-sm font-bold">Founder record unavailable</div><button onClick={() => navigate("/sourcing")} className="mt-3 text-xs font-bold text-accent">Back to discover</button></div>;

  const profile = buildFounderProfile(founder);
  const externalLinks = candidateExternalLinks(founder);
  const founderAssessment = profile.assessments.find((assessment) => assessment.title === "Founder");
  const runResearch = async () => {
    setResearchState("queued");
    try { await researchCandidate(founder.id); } catch { setResearchState("error"); }
  };

  return <div className="mx-auto max-w-[1180px] pb-10">
    {error && <div className="mb-5"><ApiStateNotice error={error} onRetry={() => void refetch()} label="founder evidence" /></div>}
    <button onClick={() => navigate("/sourcing")} className="mb-5 flex items-center gap-2 text-xs font-semibold text-muted hover:text-accent"><ArrowLeft className="h-4 w-4" /> Back to discover</button>

    <header className="panel mb-6 rounded-lg p-5 md:p-6"><div className="flex flex-col justify-between gap-5 md:flex-row md:items-center"><div className="flex items-center gap-4"><CandidateAvatar name={founder.display_name} avatarUrl={founder.avatar_url} className="h-16 w-16 rounded-lg bg-gradient-to-br from-[#dce6f2] to-[#c6d3e3] text-lg font-bold text-accent" /><div><div className="flex items-center gap-2"><h1 className="text-[1.75rem] font-bold leading-tight tracking-[-0.03em]">{founder.display_name}</h1></div><div className="mt-1 flex items-center gap-2 text-sm font-semibold text-ink-2"><Building2 className="h-3.5 w-3.5 text-accent-muted" /> {profile.role} · {profile.company}</div><div className="mt-2 flex flex-wrap gap-3 text-xs text-muted"><span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{profile.location}</span><span>{profile.stage}</span><span>{profile.sector}</span></div>{externalLinks.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{externalLinks.map((link) => { const Icon = candidateLinkIcons[link.kind]; return <a key={link.kind} href={link.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-md bg-white/75 px-2.5 py-1.5 text-[11px] font-bold text-ink-2 shadow-sm transition hover:-translate-y-0.5 hover:text-accent hover:shadow-md"><Icon className="h-3.5 w-3.5" />{link.label}<ExternalLink className="h-3 w-3 text-muted-2" /></a>; })}</div>}</div></div><div className="flex flex-wrap items-center gap-2"><button onClick={runResearch} disabled={researchState === "queued"} className="inline-flex items-center gap-2 rounded-md bg-[#eee8f8] px-4 py-3 text-[11px] font-bold text-[#7656a5] disabled:opacity-60"><Sparkles className="h-3.5 w-3.5" />{researchState === "queued" ? "Tavily research queued" : researchState === "error" ? "Research failed · retry" : "Research with Tavily"}</button></div></div></header>

    <section className="mb-6 grid gap-3 sm:grid-cols-3"><KeyMetricCard icon={Target} label="Thesis match" value={profile.thesisFit} suffix="%" detail="Fit with the active fund strategy" progress={profile.thesisFit} progressLabel={founder.thesis_match?.hard_eligible ? "Hard constraints passed" : "Review constraints"} tone="purple" /><KeyMetricCard icon={UserRound} label="Founder signal" value={profile.founderScore} suffix="/100" detail="Traits, track record and execution evidence" progress={profile.founderScore} progressLabel={founderAssessment?.rating ?? "Assessment pending"} tone="green" /><KeyMetricCard icon={ShieldCheck} label="Evidence coverage" value={profile.coverageScore} suffix="%" detail="Breadth across identity, product, traction and market" progress={profile.coverageScore} progressLabel={`${profile.claims.length} evidence records`} tone="blue" /></section>

    {founder.thesis_match && <section className="panel mb-6 rounded-lg p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="eyebrow mb-2">Thesis alignment</div><h2 className="text-base font-bold">Why this opportunity received {displayScore(founder.thesis_match.score)}</h2><p className="supporting-text mt-1"><span className="numeric">{founder.thesis_match.version} · {displayScore(founder.thesis_match.confidence)}</span> evidence confidence · {founder.thesis_match.hard_eligible ? "Hard constraints passed" : "Hard constraint failed"}</p></div></div><div className="mt-4 grid gap-3 md:grid-cols-3"><FounderThesisReasons icon={CheckCircle2} label="Matched" values={founder.thesis_match.matched} tone="green" /><FounderThesisReasons icon={AlertTriangle} label="Outside thesis" values={founder.thesis_match.failed} tone="amber" /><FounderThesisReasons icon={CircleHelp} label="Unknown" values={founder.thesis_match.unknown} tone="blue" /></div></section>}

    <div className="mb-5"><div className="eyebrow mb-2">Independent assessment</div><h2 className="text-xl font-bold">Multi-Axis Screening</h2><p className="mt-1 text-xs text-muted">Three separate views of the opportunity. They are deliberately not averaged into one score.</p></div>
    <div className="grid gap-4 xl:grid-cols-3">{profile.assessments.map((assessment) => <FounderAssessmentCard key={assessment.title} assessment={assessment} profile={profile} history={profile.axisTrendHistory[assessment.title]} />)}</div>

    <section className="panel mt-5 rounded-lg p-5"><div className="flex items-end justify-between gap-3"><div><div className="eyebrow mb-2">Source-backed research</div><h2 className="section-title">Tavily evidence & claims</h2><p className="supporting-text mt-1">Public sources used by the three independent assessments.</p></div><span className="status-pill numeric bg-accent-soft text-accent">{profile.claims.length} records</span></div>{profile.claims.length === 0 ? <div className="mt-4 rounded-md bg-surface-2 p-4 text-xs text-muted">No research claims stored yet. Run Tavily research to populate this section.</div> : <div className="mt-4 grid gap-2 lg:grid-cols-2">{profile.claims.map((claim, index) => { const sourceUrl = safeHttpUrl(claim.source); return <div key={`${claim.claim}-${index}`} className="rounded-md bg-surface-2/80 p-3.5"><div className="flex items-start justify-between gap-3"><p className="text-xs font-semibold leading-5 text-ink-2">{claim.claim}</p><span className="numeric shrink-0 rounded bg-white px-2 py-1 text-[10px] font-bold text-muted">{claim.trust}% trust</span></div><div className="mt-2 flex items-center justify-between gap-2 text-[10px] text-muted"><span>{claim.status}</span>{sourceUrl ? <a href={sourceUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-bold text-accent">Open source <ExternalLink className="h-3 w-3" /></a> : <span>{claim.source}</span>}</div></div>; })}</div>}</section>

    <div className="mt-5 flex items-start gap-3 rounded-lg bg-white/70 px-5 py-4 shadow-[0_12px_34px_rgba(70,91,120,.08)] backdrop-blur-xl"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-[#eef0f8] text-[#6676a2]"><BrainCircuit className="h-4 w-4" /></span><div><div className="text-[13px] font-bold">Feedback to Memory</div><p className="mt-1 text-xs leading-5 text-muted">Each assessment, trend change and investor correction is stored as a new version. Future screening improves without rewriting the historical decision context.</p></div><RefreshCw className="ml-auto mt-1 h-4 w-4 shrink-0 text-muted-2" /></div>
  </div>;
}
