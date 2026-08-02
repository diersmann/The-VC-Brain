import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  AlertTriangle,
  AtSign,
  BrainCircuit,
  Building2,
  CheckCircle2,
  CircleGauge,
  CircleHelp,
  ExternalLink,
  FileText,
  Github,
  Globe2,
  Lightbulb,
  Linkedin,
  MapPin,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
  UserRound,
} from "lucide-react";
import { fetchResearchStatus, researchCandidate, useCandidate } from "../api/candidates";
import { CandidateAvatar } from "../components/common/CandidateAvatar";
import { ApiStateNotice } from "../components/common/ApiStateNotice";
import { KeyMetricCard } from "../components/common/KeyMetricCard";
import { buildFounderProfile } from "../data/candidateProfile";
import { candidateExternalLinks, safeHttpUrl, type CandidateLinkKind } from "../data/candidateLinks";
import type { FounderAssessment, FounderProfile } from "../types/profile";

const axisDetails = {
  Founder: {
    icon: UserRound,
    description: "Who they are, their traits and track record.",
    checks: ["Technical capability", "Execution history", "Team building"],
    color: "#6f8db7",
    soft: "bg-[#e7eef9] text-[#5074a8]",
  },
  Market: {
    icon: Globe2,
    description: "Market sizing, competitors and SWOT.",
    checks: ["Market size", "Competitive landscape", "Tailwinds & risks"],
    color: "#4f9b84",
    soft: "bg-[#e4f2ed] text-[#347c67]",
  },
  "Idea × Market": {
    icon: Lightbulb,
    description: "Does the idea survive scrutiny, or can the team pivot?",
    checks: ["Problem strength", "Solution fit", "Pivot capacity"],
    color: "#8b6db6",
    soft: "bg-[#eee8f8] text-[#7656a5]",
  },
};

export function FounderProfilePage() {
  const { founderId } = useParams();
  const navigate = useNavigate();
  const { data: founder, isLoading, error, refetch } = useCandidate(founderId);
  const [researchState, setResearchState] = useState<"idle" | "queued" | "error">("idle");
  const researchStatus = useQuery({
    queryKey: ["research-status", founderId],
    queryFn: ({ signal }) => fetchResearchStatus(founderId!, signal),
    enabled: Boolean(founderId),
    refetchInterval: researchState === "queued" ? 2_000 : false,
  });

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
    try {
      await researchCandidate(founder.id);
    } catch {
      setResearchState("error");
    }
  };

  return (
    <div className="mx-auto max-w-[1180px] pb-10">
      {error && <div className="mb-5"><ApiStateNotice error={error} onRetry={() => void refetch()} label="founder evidence" /></div>}
      <button onClick={() => navigate("/sourcing")} className="mb-5 flex items-center gap-2 text-xs font-semibold text-muted hover:text-accent">
        <ArrowLeft className="h-4 w-4" /> Back to discover
      </button>

      <header className="panel mb-6 rounded-lg p-5 md:p-6">
        <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
          <div className="flex items-center gap-4">
            <CandidateAvatar
              name={founder.display_name}
              avatarUrl={founder.avatar_url}
              className="h-16 w-16 rounded-lg bg-gradient-to-br from-[#dce6f2] to-[#c6d3e3] text-lg font-bold text-accent"
            />
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-[1.75rem] font-bold leading-tight tracking-[-0.03em]">{founder.display_name}</h1>
              </div>
              <div className="mt-1 flex items-center gap-2 text-sm font-semibold text-ink-2">
                <Building2 className="h-3.5 w-3.5 text-accent-muted" /> {profile.role} · {profile.company}
              </div>
              <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted">
                <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{profile.location}</span>
                <span>{profile.stage}</span><span>{profile.sector}</span>
              </div>
              {externalLinks.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {externalLinks.map((link) => {
                    const Icon = candidateLinkIcons[link.kind];
                    return <a key={link.kind} href={link.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-md bg-white/75 px-2.5 py-1.5 text-[11px] font-bold text-ink-2 shadow-sm transition hover:-translate-y-0.5 hover:text-accent hover:shadow-md"><Icon className="h-3.5 w-3.5" />{link.label}<ExternalLink className="h-3 w-3 text-muted-2" /></a>;
                  })}
                </div>
              )}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button onClick={runResearch} disabled={researchState === "queued"} className="inline-flex items-center gap-2 rounded-md bg-[#eee8f8] px-4 py-3 text-[11px] font-bold text-[#7656a5] disabled:opacity-60"><Sparkles className="h-3.5 w-3.5" />{researchState === "queued" ? "Tavily research queued" : researchState === "error" ? "Research failed · retry" : "Research with Tavily"}</button>
          </div>
        </div>
      </header>

      <section className="mb-6 grid gap-3 sm:grid-cols-3">
        <KeyMetricCard icon={Target} label="Thesis match" value={profile.thesisFit} suffix="%" detail="Fit with the active fund strategy" progress={profile.thesisFit} progressLabel={founder.thesis_match?.hard_eligible ? "Hard constraints passed" : "Review constraints"} tone="purple" />
        <KeyMetricCard icon={UserRound} label="Founder signal" value={profile.founderScore} suffix="/100" detail="Traits, track record and execution evidence" progress={profile.founderScore} progressLabel={founderAssessment?.rating ?? "Assessment pending"} tone="green" />
        <KeyMetricCard icon={ShieldCheck} label="Evidence coverage" value={profile.coverageScore} suffix="%" detail="Breadth across identity, product, traction and market" progress={profile.coverageScore} progressLabel={`${profile.claims.length} evidence records`} tone="blue" />
      </section>

      {founder.thesis_match && (
        <section className="panel mb-6 rounded-lg p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="eyebrow mb-2">Thesis alignment</div>
              <h2 className="text-base font-bold">Why this opportunity received {Math.round(founder.thesis_match.score * 100)}%</h2>
              <p className="supporting-text mt-1"><span className="numeric">{founder.thesis_match.version} · {Math.round(founder.thesis_match.confidence * 100)}%</span> evidence confidence · {founder.thesis_match.hard_eligible ? "Hard constraints passed" : "Hard constraint failed"}</p>
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <ThesisReasons icon={CheckCircle2} label="Matched" values={founder.thesis_match.matched} tone="green" />
            <ThesisReasons icon={AlertTriangle} label="Outside thesis" values={founder.thesis_match.failed} tone="amber" />
            <ThesisReasons icon={CircleHelp} label="Unknown" values={founder.thesis_match.unknown} tone="blue" />
          </div>
        </section>
      )}

      <div className="mb-5">
        <div className="eyebrow mb-2">Independent assessment</div>
        <h2 className="text-xl font-bold">Multi-Axis Screening</h2>
        <p className="mt-1 text-xs text-muted">Three separate views of the opportunity. They are deliberately not averaged into one score.</p>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        {profile.assessments.map((assessment) => (
          <AxisCard key={assessment.title} assessment={assessment} profile={profile} history={profile.axisTrendHistory[assessment.title]} />
        ))}
      </div>

      <section className="panel mt-5 rounded-lg p-5">
        <div className="flex items-end justify-between gap-3">
          <div><div className="eyebrow mb-2">Source-backed research</div><h2 className="section-title">Tavily evidence & claims</h2><p className="supporting-text mt-1">Public sources used by the three independent assessments.</p></div>
          <span className="status-pill numeric bg-accent-soft text-accent">{profile.claims.length} records</span>
        </div>
        {profile.claims.length === 0 ? <div className="mt-4 rounded-md bg-surface-2 p-4 text-xs text-muted">No research claims stored yet. Run Tavily research to populate this section.</div> : <div className="mt-4 grid gap-2 lg:grid-cols-2">{profile.claims.map((claim, index) => { const sourceUrl = safeHttpUrl(claim.source); return <div key={`${claim.claim}-${index}`} className="rounded-md bg-surface-2/80 p-3.5"><div className="flex items-start justify-between gap-3"><p className="text-xs font-semibold leading-5 text-ink-2">{claim.claim}</p><span className="numeric shrink-0 rounded bg-white px-2 py-1 text-[10px] font-bold text-muted">{claim.trust}% trust</span></div><div className="mt-2 flex items-center justify-between gap-2 text-[10px] text-muted"><span>{claim.status}</span>{sourceUrl ? <a href={sourceUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-bold text-accent">Open source <ExternalLink className="h-3 w-3" /></a> : <span>{claim.source}</span>}</div></div>; })}</div>}
      </section>

      <div className="mt-5 flex items-start gap-3 rounded-lg bg-white/70 px-5 py-4 shadow-[0_12px_34px_rgba(70,91,120,.08)] backdrop-blur-xl">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-[#eef0f8] text-[#6676a2]"><BrainCircuit className="h-4 w-4" /></span>
        <div><div className="text-[13px] font-bold">Feedback to Memory</div><p className="mt-1 text-xs leading-5 text-muted">Each assessment, trend change and investor correction is stored as a new version. Future screening improves without rewriting the historical decision context.</p></div>
        <RefreshCw className="ml-auto mt-1 h-4 w-4 shrink-0 text-muted-2" />
      </div>
    </div>
  );
}

const candidateLinkIcons: Record<CandidateLinkKind, React.ElementType> = {
  linkedin: Linkedin,
  github: Github,
  website: Globe2,
  deck: FileText,
  x: AtSign,
};

function ThesisReasons({ icon: Icon, label, values, tone }: { icon: React.ElementType; label: string; values: string[]; tone: "green" | "amber" | "blue" }) {
  const colors = {
    green: "bg-[#e4f2ed] text-[#347c67]",
    amber: "bg-[#fff1df] text-[#a96e2d]",
    blue: "bg-[#e7eef9] text-[#5074a8]",
  };
  return <div className={`rounded-md p-3.5 ${colors[tone]}`}><div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider"><Icon className="h-3.5 w-3.5" />{label}</div><div className="mt-2 text-xs font-semibold">{values.length ? values.join(" · ") : "None"}</div></div>;
}

function AxisCard({ assessment, profile, history }: { assessment: FounderAssessment; profile: FounderProfile; history: number[] }) {
  const details = axisDetails[assessment.title];
  const Icon = details.icon;
  const values = history.length ? history.slice(-5) : assessment.score == null ? [] : [assessment.score];
  const ratingStyle = assessment.rating === "Bullish"
    ? "bg-[#e4f2ed] text-success"
    : assessment.rating === "Bearish"
      ? "bg-[#fbe8e9] text-danger"
      : "bg-[#fff1df] text-warn";
  const TrendIcon = assessment.trend === "Declining" ? TrendingDown : assessment.trend === "Improving" ? TrendingUp : CircleGauge;
  const explanation = axisExplanation(assessment.title, profile);

  return (
    <article className="panel overflow-hidden rounded-lg">
      <div className="p-5">
        <div className="flex items-start justify-between gap-3">
          <span className={`flex h-10 w-10 items-center justify-center rounded-md ${details.soft}`}><Icon className="h-5 w-5" /></span>
          <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${ratingStyle}`}>{assessment.rating}</span>
        </div>
        <h3 className="mt-4 text-base font-bold">{assessment.title}</h3>
        <p className="mt-1 text-xs leading-5 text-muted">{details.description}</p>

        <div className="mt-4 rounded-md bg-surface-2/80 p-3 shadow-inner shadow-white/80">
          <div className="data-label">Why this rating</div>
          <p className="mt-1.5 text-xs font-medium leading-5 text-ink-2">{assessment.body}</p>
        </div>

        <div className="mt-4 space-y-3 rounded-md bg-white/55 p-3">
          <InsightRow kind="support" label="Supporting evidence" text={explanation.support} meta={explanation.supportMeta} />
          <InsightRow kind="risk" label="Counter-evidence / risk" text={explanation.risk} />
          <InsightRow kind="unknown" label="Still unknown" text={explanation.unknown} />
        </div>
      </div>

      <div className="bg-gradient-to-br from-surface-2 to-[#edf4f4] px-5 pb-4 pt-4">
        <div className="mb-2 flex items-center justify-between">
          <div><div className="data-label">Trend · last 5 updates</div><div className="mt-1 flex items-center gap-1.5 text-xs font-bold" style={{ color: details.color }}><TrendIcon className="h-3.5 w-3.5" />{assessment.trend}</div></div>
          <div className="text-right"><div className="numeric text-xl font-bold leading-none">{values.at(-1) ?? "—"}</div><div className="mt-1 text-[10px] text-muted">Current signal</div></div>
        </div>
        {values.length ? <TrendChart values={values} color={details.color} /> : <div className="flex h-[92px] items-center justify-center text-xs text-muted">No measured signal yet.</div>}
        <div className="mt-1 flex justify-between text-[10px] text-muted-2"><span>Earlier evidence</span><span>Latest</span></div>
        <div className="mt-3 rounded-md bg-white/55 p-3">
          <div className="data-label mb-1.5 flex items-center justify-between"><span>Assessment confidence</span><span className="numeric">{assessment.confidence}%</span></div>
          <div className="h-1.5 bg-surface-3"><div className="h-full" style={{ width: `${assessment.confidence}%`, backgroundColor: details.color }} /></div>
          <p className="mt-2 text-[10px] leading-4 text-muted">Each point is a versioned Memory update based on new evidence or an investor correction.</p>
        </div>
      </div>
    </article>
  );
}

function InsightRow({ kind, label, text, meta }: { kind: "support" | "risk" | "unknown"; label: string; text: string; meta?: string }) {
  const styles = kind === "support"
    ? { dot: "bg-success", label: "text-success" }
    : kind === "risk"
      ? { dot: "bg-danger", label: "text-danger" }
      : { dot: "bg-warn", label: "text-warn" };
  return <div className="flex gap-2.5"><span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${styles.dot}`} /><div><div className={`text-[10px] font-bold uppercase tracking-wider ${styles.label}`}>{label}</div><p className="mt-1 text-[11px] leading-[1.55] text-ink-2">{text}</p>{meta && <div className="numeric mt-1 text-[10px] text-muted">{meta}</div>}</div></div>;
}

function axisExplanation(axis: FounderAssessment["title"], profile: FounderProfile) {
  const strongestClaim = [...profile.claims].sort((a, b) => b.trust - a.trust)[0];
  const latestEvent = profile.events[0];
  if (axis === "Founder") {
    const trust = latestEvent?.trust ?? profile.sourceConfidence;
    return {
      support: latestEvent?.body ?? profile.scoreHint,
      supportMeta: `${latestEvent?.type ?? "Track record"} · Trust ${trust == null ? "Not scored" : `${trust}%`}`,
      risk: profile.gaps.at(-1) ?? "Team-building evidence remains limited.",
      unknown: "Performance under sustained fundraising and scaling pressure.",
    };
  }
  if (axis === "Market") {
    const marketCoverage = profile.coverage.at(-1);
    const trust = strongestClaim?.trust ?? profile.sourceConfidence;
    return {
      support: `${profile.sector} demand is supported by: ${strongestClaim?.claim ?? profile.signal}.`,
      supportMeta: `${strongestClaim?.status ?? "Supported"} · Trust ${trust == null ? "Not scored" : `${trust}%`}`,
      risk: profile.gaps[1] ?? profile.gaps[0] ?? "Competitive response needs deeper review.",
      unknown: `${marketCoverage?.label ?? "Bottom-up market size"} is only ${marketCoverage?.value ?? 50}% evidenced.`,
    };
  }
  const trust = profile.claims[1]?.trust ?? profile.sourceConfidence;
  return {
    support: profile.signal,
    supportMeta: `${profile.claims[1]?.source ?? "Product and traction evidence"} · Trust ${trust == null ? "Not scored" : `${trust}%`}`,
    risk: profile.gaps[0] ?? "Repeatable customer demand has not been independently verified.",
    unknown: "Whether the current wedge scales without a material product pivot.",
  };
}

function TrendChart({ values, color }: { values: number[]; color: string }) {
  const width = 300; const height = 92; const pad = 8;
  const min = Math.min(...values) - 5; const max = Math.max(...values) + 5;
  const points = values.map((value, index) => {
    const x = values.length === 1 ? width / 2 : pad + index * ((width - pad * 2) / (values.length - 1));
    const y = height - pad - ((value - min) / Math.max(1, max - min)) * (height - pad * 2);
    return { x, y, value };
  });
  const line = points.map((point) => `${point.x},${point.y}`).join(" ");
  const area = `${pad},${height - pad} ${line} ${width - pad},${height - pad}`;
  return <svg viewBox={`0 0 ${width} ${height}`} className="h-[92px] w-full" role="img" aria-label={`Trend values ${values.join(", ")}`}>
    <defs><linearGradient id={`area-${color.replace("#", "")}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={color} stopOpacity=".24"/><stop offset="100%" stopColor={color} stopOpacity="0"/></linearGradient></defs>
    {[25,50,75].map(y=><line key={y} x1="8" y1={y} x2="292" y2={y} stroke="#dfe6ef" strokeWidth="1" strokeDasharray="3 4"/>)}
    <polygon points={area} fill={`url(#area-${color.replace("#", "")})`} />
    <polyline points={line} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    {points.map((point,index)=><circle key={index} cx={point.x} cy={point.y} r={index===points.length-1?4:2.5} fill="white" stroke={color} strokeWidth="2" />)}
  </svg>;
}
