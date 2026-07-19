import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  Building2,
  Check,
  CheckCircle2,
  Clock3,
  DollarSign,
  FileText,
  Lightbulb,
  Mail,
  MapPin,
  Minus,
  PauseCircle,
  Scale,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
  Users,
  X,
} from "lucide-react";
import { Link, useParams } from "react-router";
import { useCandidate } from "../api/candidates";
import { CandidateAvatar } from "../components/common/CandidateAvatar";
import { buildFounderProfile, formatPredicate } from "../data/candidateProfile";
import type { CandidateDetail } from "../types/candidate";
import type { FounderAssessment, FounderProfile } from "../types/profile";

type DecisionMeta = {
  recommendation: "Proceed" | "Hold" | "Investigate";
  deadline: string;
  ask: string;
  targetOwnership: string;
  round: string;
  valuation: string;
  lead: string;
  aiSummary: string;
  thesis: string;
  product: string;
  traction: string[];
  market: string;
  competition: string;
  strengths: string[];
  risks: string[];
  conditions: string[];
};

export function DecisionDetailPage() {
  const { founderId } = useParams();
  const { data: candidate, isLoading, error } = useCandidate(founderId);

  if (isLoading) return <div className="py-20 text-center text-sm text-muted">Loading investment evidence…</div>;
  if (error || !candidate) return <div className="py-20 text-center"><div className="text-sm font-bold">Decision candidate not found</div><Link to="/decisions" className="mt-3 inline-block text-xs font-bold text-accent">Back to decision queue</Link></div>;

  const profile = buildFounderProfile(candidate);
  const meta = createDecisionMeta(profile, candidate);

  return (
    <div className="mx-auto max-w-[1240px] pb-12">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <Link
          to="/decisions"
          className="inline-flex items-center gap-2 text-xs font-bold text-muted transition-colors hover:text-ink"
        >
          <ArrowLeft className="h-4 w-4" /> Back to decision queue
        </Link>
        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.12em] text-muted">
          <Clock3 className="h-3.5 w-3.5 text-amber-600" /> Decision due in {meta.deadline}
        </div>
      </div>

      <div className="grid items-start gap-5 lg:grid-cols-[270px_minmax(0,1fr)]">
        <FounderSidebar profile={profile} candidate={candidate} meta={meta} />

        <main className="min-w-0 space-y-5">
          <AiSummary profile={profile} meta={meta} />
          <DealMetrics profile={profile} meta={meta} />
          <AxisScreening profile={profile} />
          <InvestmentMemo profile={profile} meta={meta} />

          <div className="grid gap-5 xl:grid-cols-2">
            <ListCard
              title="Key risks"
              eyebrow="Downside case"
              icon={AlertTriangle}
              items={meta.risks}
              tone="amber"
            />
            <ListCard
              title="Conditions to proceed"
              eyebrow="Next diligence"
              icon={CheckCircle2}
              items={meta.conditions}
              tone="blue"
            />
          </div>

          <EvidenceCard profile={profile} />
          <DecisionActions recommendation={meta.recommendation} />
        </main>
      </div>
    </div>
  );
}

function FounderSidebar({
  profile,
  candidate,
  meta,
}: {
  profile: FounderProfile;
  candidate: CandidateDetail;
  meta: DecisionMeta;
}) {
  return (
    <aside className="panel overflow-hidden rounded-lg lg:sticky lg:top-5">
      <div className="h-16 bg-gradient-to-r from-[#dfeafa] via-[#e8eef9] to-[#e8f3ef]" />
      <div className="px-5 pb-5">
        <CandidateAvatar
          name={candidate.display_name}
          avatarUrl={candidate.avatar_url}
          className="-mt-9 mb-4 h-[72px] w-[72px] rounded-lg border-4 border-white bg-accent text-xl font-bold text-white shadow-sm"
        />
        <h1 className="text-xl font-bold tracking-tight">{candidate.display_name ?? "Unknown founder"}</h1>
        <p className="mt-1 text-xs font-semibold text-ink-2">{profile.role}</p>
        <p className="text-xs text-muted">{profile.company}</p>

        <div className="mt-4 space-y-2.5 rounded-md bg-surface-2/75 p-3.5 text-[11px] text-muted">
          <SidebarRow icon={MapPin} value={profile.location} />
          <SidebarRow icon={Building2} value={`${profile.stage} · ${profile.sector}`} />
          <SidebarRow icon={Mail} value={candidate.email ?? "Email not provided"} />
          <SidebarRow icon={Target} value={`Origin: ${candidate.origin}`} />
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2">
          <SmallMetric label="Thesis fit" value={`${profile.thesisFit}%`} />
          <SmallMetric label="Evidence" value={`${profile.evidence}%`} />
        </div>

        <div className="mt-4 flex flex-wrap gap-1.5">
          {profile.tags.slice(0, 5).map((tag) => (
            <span key={tag} className="rounded bg-surface-2 px-2 py-1 text-[9px] font-semibold text-muted">
              {tag}
            </span>
          ))}
        </div>

        <Link
          to={`/founders/${candidate.id}`}
          className="mt-5 flex w-full items-center justify-center rounded-md bg-white/75 py-2.5 text-[11px] font-bold text-ink-2 shadow-sm transition-all hover:-translate-y-0.5 hover:text-accent hover:shadow-md"
        >
          Open full founder profile
        </Link>

        <div className="mt-5 rounded-md bg-surface-2 p-3">
          <div className="text-[9px] font-bold uppercase tracking-wider text-muted-2">Round context</div>
          <div className="mt-2 flex items-center justify-between text-[11px]">
            <span className="text-muted">Ask</span>
            <span className="font-bold">{meta.ask}</span>
          </div>
          <div className="mt-1.5 flex items-center justify-between text-[11px]">
            <span className="text-muted">Target ownership</span>
            <span className="font-bold">{meta.targetOwnership}</span>
          </div>
          <div className="mt-1.5 flex items-center justify-between text-[11px]">
            <span className="text-muted">Lead status</span>
            <span className="font-bold">{meta.lead}</span>
          </div>
        </div>
      </div>
    </aside>
  );
}

function AiSummary({ profile, meta }: { profile: FounderProfile; meta: DecisionMeta }) {
  const styles = {
    Proceed: "bg-[#e4f2ed] text-[#347c67]",
    Hold: "bg-[#fff1df] text-[#a96e2d]",
    Investigate: "bg-[#e7eef9] text-[#5074a8]",
  };

  return (
    <section className="panel relative overflow-hidden rounded-lg p-5 sm:p-6">
      <div className="pointer-events-none absolute -right-12 -top-16 h-44 w-44 rounded-full bg-[#d9e5f7]/75 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-16 left-1/4 h-32 w-32 rounded-full bg-[#dff0ea]/70 blur-3xl" />
      <div className="relative">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="eyebrow mb-2 flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5" /> AI investment summary
          </div>
          <h2 className="text-xl font-bold tracking-tight">{profile.company} at a glance</h2>
        </div>
        <span className={`rounded-md px-3 py-1.5 text-[10px] font-bold ${styles[meta.recommendation]}`}>
          {meta.recommendation}
        </span>
      </div>
      <p className="mt-4 max-w-[900px] text-sm leading-7 text-ink-2">{meta.aiSummary}</p>
      <div className="mt-4 flex items-center gap-2 text-[9px] font-semibold text-muted-2">
        <ShieldCheck className="h-3.5 w-3.5 text-accent" /> Generated from available evidence; key claims still require human verification.
      </div>
      </div>
    </section>
  );
}

function DealMetrics({ profile, meta }: { profile: FounderProfile; meta: DecisionMeta }) {
  const metrics = [
    { label: "Round", value: meta.round, detail: meta.valuation, icon: DollarSign, color: "text-[#5074a8] bg-[#e7eef9]" },
    { label: "Thesis match", value: `${profile.thesisFit}%`, detail: "Fund strategy fit", icon: Target, color: "text-[#7d64ad] bg-[#eee9f7]" },
    { label: "Founder signal", value: `${profile.founderScore}/100`, detail: profile.signal, icon: Users, color: "text-[#347c67] bg-[#e4f2ed]" },
    { label: "Evidence quality", value: `${profile.evidence}%`, detail: "Source-weighted", icon: ShieldCheck, color: "text-[#a96e2d] bg-[#fff1df]" },
  ];

  return (
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {metrics.map(({ label, value, detail, icon: Icon, color }) => (
        <div key={label} className="panel rounded-lg p-4">
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-bold uppercase tracking-wider text-muted-2">{label}</span>
            <span className={`flex h-7 w-7 items-center justify-center rounded-md ${color}`}>
              <Icon className="h-3.5 w-3.5" />
            </span>
          </div>
          <div className="mt-2 text-lg font-bold">{value}</div>
          <div className="mt-1 truncate text-[10px] text-muted">{detail}</div>
        </div>
      ))}
    </section>
  );
}

function AxisScreening({ profile }: { profile: FounderProfile }) {
  return (
    <section className="panel rounded-lg p-5 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="eyebrow mb-2">Decision quality</div>
          <h2 className="text-lg font-bold">Multi-axis screening</h2>
          <p className="mt-1 text-[11px] text-muted">Three independent scores — intentionally not averaged.</p>
        </div>
      </div>
      <div className="mt-5 grid gap-3 xl:grid-cols-3">
        {profile.assessments.map((assessment) => (
          <AxisCard
            key={assessment.title}
            assessment={assessment}
            score={assessment.score}
            values={profile.axisTrendHistory[assessment.title]}
          />
        ))}
      </div>
    </section>
  );
}

function AxisCard({ assessment, score, values }: { assessment: FounderAssessment; score: number; values: number[] }) {
  const TrendIcon = assessment.trend === "Improving" ? TrendingUp : assessment.trend === "Declining" ? TrendingDown : Minus;
  const tone = assessment.rating === "Bullish" ? "#347c67" : assessment.rating === "Bearish" ? "#b65d5d" : "#a96e2d";
  const trendData = values.length ? values.slice(-5) : [score];
  const change = score - trendData[0];

  return (
    <article
      className="rounded-lg p-4 shadow-[0_10px_28px_rgba(70,91,120,.07)]"
      style={{ background: `linear-gradient(145deg, ${tone}12, rgba(255,255,255,.88) 58%)` }}
    >
      <div className="flex items-center justify-between gap-2">
        <div>
          <div className="text-xs font-bold">{assessment.title}</div>
          <div className="mt-1 flex items-center gap-1 text-[9px] font-bold" style={{ color: tone }}>
            <TrendIcon className="h-3 w-3" /> {assessment.rating} · {assessment.trend}
          </div>
        </div>
        <div className="text-right">
          <div className="text-xl font-bold" style={{ color: tone }}>{score}</div>
          <div className="text-[8px] uppercase tracking-wider text-muted-2">axis score</div>
        </div>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-2">
        <div className="h-full rounded-full" style={{ width: `${score}%`, backgroundColor: tone }} />
      </div>
      <div className="mt-3 rounded-md bg-white/60 px-3 pb-2 pt-3 shadow-inner shadow-white/80 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <span className="text-[8px] font-bold uppercase tracking-wider text-muted-2">Trend · last 5 updates</span>
          <span className="text-[9px] font-bold" style={{ color: tone }}>
            {change > 0 ? "+" : ""}{change} pts
          </span>
        </div>
        <AxisTrendChart values={trendData} color={tone} label={`${assessment.title} ${assessment.trend} trend`} />
        <div className="flex justify-between text-[8px] text-muted-2">
          <span>Earlier evidence</span>
          <span>Latest</span>
        </div>
      </div>
      <p className="mt-3 text-[10px] leading-5 text-muted">{assessment.body}</p>
      <div className="mt-3 rounded bg-white/55 px-2.5 py-2 text-[9px] text-muted-2">
        Confidence <span className="font-bold text-ink-2">{assessment.confidence}%</span>
      </div>
    </article>
  );
}

function AxisTrendChart({ values, color, label }: { values: number[]; color: string; label: string }) {
  const width = 260;
  const height = 72;
  const padding = 7;
  const minimum = Math.min(...values) - 5;
  const maximum = Math.max(...values) + 5;
  const points = values.map((value, index) => ({
    x: values.length === 1 ? width / 2 : padding + index * ((width - padding * 2) / (values.length - 1)),
    y: height - padding - ((value - minimum) / Math.max(1, maximum - minimum)) * (height - padding * 2),
  }));
  const line = points.map((point) => `${point.x},${point.y}`).join(" ");
  const area = `${padding},${height - padding} ${line} ${width - padding},${height - padding}`;
  const gradientId = `decision-trend-${label.replace(/[^a-z0-9]/gi, "-").toLowerCase()}`;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="mt-1 h-[72px] w-full" role="img" aria-label={`${label}: ${values.join(", ")}`}>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.22" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {[22, 44, 66].map((y) => (
        <line key={y} x1={padding} y1={y} x2={width - padding} y2={y} stroke="#dfe6ef" strokeWidth="1" strokeDasharray="3 4" />
      ))}
      <polygon points={area} fill={`url(#${gradientId})`} />
      <polyline points={line} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      {points.map((point, index) => (
        <circle
          key={`${point.x}-${point.y}`}
          cx={point.x}
          cy={point.y}
          r={index === points.length - 1 ? 3.5 : 2.25}
          fill="white"
          stroke={color}
          strokeWidth="2"
        />
      ))}
    </svg>
  );
}

function InvestmentMemo({ profile, meta }: { profile: FounderProfile; meta: DecisionMeta }) {
  return (
    <section className="panel rounded-lg p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-gradient-to-r from-[#edf3fb] to-[#eef6f3] px-4 py-3.5">
        <div>
          <div className="eyebrow mb-2 flex items-center gap-1.5"><FileText className="h-3.5 w-3.5" /> Investment memo</div>
          <h2 className="text-lg font-bold">Detailed IC report</h2>
        </div>
        <span className="rounded bg-surface-2 px-2.5 py-1 text-[9px] font-bold text-muted">Draft · AI assisted</span>
      </div>

      <div className="mt-5 grid gap-x-7 gap-y-6 xl:grid-cols-2">
        <MemoSection icon={Lightbulb} title="Investment thesis" text={meta.thesis} />
        <MemoSection icon={Building2} title="Company & product" text={meta.product} />
        <MemoSection icon={BarChart3} title="Market assessment" text={meta.market} />
        <MemoSection icon={Scale} title="Competition & moat" text={meta.competition} />

        <div>
          <MemoHeading icon={TrendingUp} title="Traction & KPIs" />
          <ul className="mt-3 space-y-2">
            {meta.traction.map((item) => (
              <li key={item} className="flex gap-2 text-[11px] leading-5 text-ink-2">
                <Check className="mt-1 h-3 w-3 shrink-0 text-[#347c67]" /> {item}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <MemoHeading icon={Users} title="Founder & team" />
          <p className="mt-3 text-[11px] leading-6 text-ink-2">{profile.summary}</p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {meta.strengths.map((item) => (
              <span key={item} className="rounded bg-[#e4f2ed] px-2 py-1 text-[9px] font-semibold text-[#347c67]">{item}</span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function MemoSection({ icon, title, text }: { icon: React.ElementType; title: string; text: string }) {
  return (
    <div>
      <MemoHeading icon={icon} title={title} />
      <p className="mt-3 text-[11px] leading-6 text-ink-2">{text}</p>
    </div>
  );
}

function MemoHeading({ icon: Icon, title }: { icon: React.ElementType; title: string }) {
  return (
    <div className="flex items-center gap-2 text-xs font-bold">
      <span className="flex h-7 w-7 items-center justify-center rounded-md bg-accent-soft text-accent"><Icon className="h-3.5 w-3.5" /></span>
      {title}
    </div>
  );
}

function ListCard({
  title,
  eyebrow,
  icon: Icon,
  items,
  tone,
}: {
  title: string;
  eyebrow: string;
  icon: React.ElementType;
  items: string[];
  tone: "amber" | "blue";
}) {
  const colors = tone === "amber" ? "bg-[#fff1df] text-[#a96e2d]" : "bg-[#e7eef9] text-[#5074a8]";
  return (
    <section className="panel rounded-lg p-5">
      <div className="flex items-center gap-3">
        <span className={`flex h-9 w-9 items-center justify-center rounded-md ${colors}`}><Icon className="h-4 w-4" /></span>
        <div><div className="text-[9px] font-bold uppercase tracking-wider text-muted-2">{eyebrow}</div><h2 className="mt-0.5 text-sm font-bold">{title}</h2></div>
      </div>
      <ul className="mt-4 space-y-3">
        {items.map((item, index) => (
          <li key={item} className="flex gap-2.5 text-[11px] leading-5 text-ink-2">
            <span className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded text-[9px] font-bold ${colors}`}>{index + 1}</span>
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}

function EvidenceCard({ profile }: { profile: FounderProfile }) {
  return (
    <section className="panel rounded-lg p-5 sm:p-6">
      <div className="flex items-center justify-between gap-3">
        <div><div className="eyebrow mb-2">Evidence quality</div><h2 className="text-lg font-bold">Critical claims</h2></div>
        <span className="text-[10px] font-bold text-muted">{profile.claims.length} claims reviewed</span>
      </div>
      <div className="mt-4 space-y-2">
        {profile.claims.map((claim) => {
          const supported = claim.status === "Supported";
          return (
            <div key={claim.claim} className="grid gap-3 rounded-md bg-surface-2/75 px-4 py-3 sm:grid-cols-[1fr_100px_120px] sm:items-center">
              <div className="text-[11px] font-semibold text-ink-2">{claim.claim}</div>
              <div className="text-[10px] text-muted">Trust <span className="font-bold text-ink">{claim.trust}%</span></div>
              <span className={`w-fit rounded px-2 py-1 text-[9px] font-bold ${supported ? "bg-[#e4f2ed] text-[#347c67]" : "bg-[#fff1df] text-[#a96e2d]"}`}>
                {claim.status}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function DecisionActions({ recommendation }: { recommendation: DecisionMeta["recommendation"] }) {
  return (
    <section className="panel rounded-lg p-5">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="text-sm font-bold">Record investment decision</div>
          <p className="mt-1 text-[10px] text-muted">AI recommendation: {recommendation}. Final approval remains with the investment team.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="inline-flex items-center gap-1.5 rounded-md bg-surface-2 px-4 py-2.5 text-[10px] font-bold text-muted shadow-sm hover:text-ink"><X className="h-3.5 w-3.5" /> Pass</button>
          <button className="inline-flex items-center gap-1.5 rounded-md border border-[#e7cda9] bg-[#fff8ed] px-4 py-2.5 text-[10px] font-bold text-[#a96e2d]"><PauseCircle className="h-3.5 w-3.5" /> Hold</button>
          <button className="inline-flex items-center gap-1.5 rounded-md bg-accent px-4 py-2.5 text-[10px] font-bold text-white"><CheckCircle2 className="h-3.5 w-3.5" /> Proceed to diligence</button>
        </div>
      </div>
    </section>
  );
}

function SidebarRow({ icon: Icon, value }: { icon: React.ElementType; value: string }) {
  return <div className="flex items-start gap-2"><Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-2" /><span className="break-all">{value}</span></div>;
}

function SmallMetric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md bg-surface-2 p-3"><div className="text-base font-bold">{value}</div><div className="mt-0.5 text-[9px] text-muted">{label}</div></div>;
}

function createDecisionMeta(profile: FounderProfile, candidate: CandidateDetail): DecisionMeta {
  const ratings = profile.assessments.filter((item) => item.rating !== "Pending").map((item) => item.rating);
  const recommendation: DecisionMeta["recommendation"] = ratings.includes("Bearish")
    ? "Hold"
    : ratings.length === 3 && ratings.every((rating) => rating === "Bullish")
      ? "Proceed"
      : "Investigate";
  const sourceCount = new Set(candidate.observations.map((item) => item.source_type)).size;
  const traction = profile.claims.length
    ? profile.claims.slice(0, 5).map((claim) => claim.claim)
    : ["No traction claims have been recorded in the evidence store."];
  const marketEvidence = candidate.observations.filter((item) => /(market|sector|industry|category)/i.test(item.predicate));
  const competitionEvidence = candidate.observations.filter((item) => /(compet|alternative|similar)/i.test(item.predicate));
  const risks = profile.gaps.length ? profile.gaps.slice(0, 4) : ["No formal risk assessment has been recorded."];

  return {
    recommendation,
    deadline: "Not scheduled",
    ask: "Not disclosed",
    targetOwnership: "Not set",
    round: profile.stage,
    valuation: "Not disclosed",
    lead: "Not recorded",
    aiSummary: `${candidate.display_name ?? candidate.stable_id} has ${candidate.observations.length} observations from ${sourceCount} public source${sourceCount === 1 ? "" : "s"}. ${profile.summary} ${profile.thesisFit ? `Recorded thesis fit is ${profile.thesisFit}%.` : "Thesis fit has not been scored."} Recommendation: ${recommendation.toLowerCase()} pending review of the listed evidence gaps.`,
    thesis: profile.thesisFit
      ? `The recorded thesis-fit score is ${profile.thesisFit}%. ${profile.summary}`
      : "No thesis-fit assessment has been stored for this candidate. The investment team should score the opportunity against the active thesis.",
    product: profile.summary,
    traction,
    market: marketEvidence.length
      ? marketEvidence.slice(0, 3).map((item) => `${formatPredicate(item.predicate)}: ${item.object_value}`).join(" ")
      : "No market-sizing or sector claim has been recorded in the evidence store.",
    competition: competitionEvidence.length
      ? competitionEvidence.slice(0, 3).map((item) => `${formatPredicate(item.predicate)}: ${item.object_value}`).join(" ")
      : "No competitive-landscape evidence has been recorded.",
    strengths: profile.tags.length ? profile.tags.slice(0, 4) : ["No verified strengths recorded"],
    risks,
    conditions: risks.map((gap) => `Resolve: ${gap}`),
  };
}
