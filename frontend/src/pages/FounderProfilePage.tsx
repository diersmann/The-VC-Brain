import { useNavigate, useParams } from "react-router";
import {
  ArrowLeft,
  BrainCircuit,
  Building2,
  CheckCircle2,
  CircleGauge,
  Globe2,
  Lightbulb,
  MapPin,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  UserRound,
} from "lucide-react";
import { mockCandidates } from "../data/mockCandidates";
import { getMockFounderProfile, type FounderAssessment } from "../data/mockFounderProfiles";

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
  const founder = mockCandidates.find((candidate) => candidate.id === founderId) ?? mockCandidates[0];
  const profile = getMockFounderProfile(founder.stable_id);

  return (
    <div className="mx-auto max-w-[1180px] pb-10">
      <button onClick={() => navigate("/sourcing")} className="mb-5 flex items-center gap-2 text-xs font-semibold text-muted hover:text-accent">
        <ArrowLeft className="h-4 w-4" /> Back to discover
      </button>

      <header className="panel mb-6 rounded-lg p-5 md:p-6">
        <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
          <div className="flex items-center gap-4">
            <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-[#dce6f2] to-[#c6d3e3] text-lg font-bold text-accent">
              {profile.initials}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight">{founder.display_name}</h1>
                <CheckCircle2 className="h-4 w-4 text-success" />
              </div>
              <div className="mt-1 flex items-center gap-2 text-sm font-semibold text-ink-2">
                <Building2 className="h-3.5 w-3.5 text-accent-muted" /> {profile.role} · {profile.company}
              </div>
              <div className="mt-1.5 flex flex-wrap gap-3 text-[11px] text-muted">
                <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{profile.location}</span>
                <span>{profile.stage}</span><span>{profile.sector}</span>
              </div>
            </div>
          </div>
          <div className="rounded-md bg-accent-soft px-4 py-3 text-right">
            <div className="text-[9px] font-bold uppercase tracking-wider text-accent-muted">Thesis match</div>
            <div className="mt-1 text-xl font-bold text-accent">{profile.thesisFit}%</div>
          </div>
        </div>
      </header>

      <div className="mb-5">
        <div className="eyebrow mb-2">Independent assessment</div>
        <h2 className="text-xl font-bold">Multi-Axis Screening</h2>
        <p className="mt-1 text-xs text-muted">Three separate views of the opportunity. They are deliberately not averaged into one score.</p>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        {profile.assessments.map((assessment, index) => (
          <AxisCard key={assessment.title} assessment={assessment} seed={profile.founderScore + index * 7} />
        ))}
      </div>

      <div className="mt-5 flex items-start gap-3 rounded-lg border border-line bg-white px-5 py-4 shadow-sm">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-[#eef0f8] text-[#6676a2]"><BrainCircuit className="h-4 w-4" /></span>
        <div><div className="text-xs font-bold">Feedback to Memory</div><p className="mt-1 text-[11px] leading-5 text-muted">Each assessment, trend change and investor correction is stored as a new version. Future screening improves without rewriting the historical decision context.</p></div>
        <RefreshCw className="ml-auto mt-1 h-4 w-4 shrink-0 text-muted-2" />
      </div>
    </div>
  );
}

function AxisCard({ assessment, seed }: { assessment: FounderAssessment; seed: number }) {
  const details = axisDetails[assessment.title];
  const Icon = details.icon;
  const values = trendValues(assessment.trend, seed);
  const ratingStyle = assessment.rating === "Bullish"
    ? "bg-[#e4f2ed] text-success"
    : assessment.rating === "Bearish"
      ? "bg-[#fbe8e9] text-danger"
      : "bg-[#fff1df] text-warn";
  const TrendIcon = assessment.trend === "Declining" ? TrendingDown : assessment.trend === "Improving" ? TrendingUp : CircleGauge;

  return (
    <article className="panel overflow-hidden rounded-lg">
      <div className="p-5">
        <div className="flex items-start justify-between gap-3">
          <span className={`flex h-10 w-10 items-center justify-center rounded-md ${details.soft}`}><Icon className="h-5 w-5" /></span>
          <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${ratingStyle}`}>{assessment.rating}</span>
        </div>
        <h3 className="mt-4 text-base font-bold">{assessment.title}</h3>
        <p className="mt-1 min-h-10 text-[11px] leading-5 text-muted">{details.description}</p>
        <div className="mt-4 space-y-2 border-t border-line pt-4">
          {details.checks.map((check) => <div key={check} className="flex items-center gap-2 text-[11px] text-ink-2"><CheckCircle2 className="h-3.5 w-3.5" style={{ color: details.color }} />{check}</div>)}
        </div>
      </div>

      <div className="border-t border-line bg-surface-2 px-5 pb-4 pt-4">
        <div className="mb-2 flex items-center justify-between">
          <div><div className="text-[9px] font-bold uppercase tracking-wider text-muted-2">Trend · last 5 updates</div><div className="mt-1 flex items-center gap-1.5 text-xs font-bold" style={{ color: details.color }}><TrendIcon className="h-3.5 w-3.5" />{assessment.trend}</div></div>
          <div className="text-right"><div className="text-lg font-bold">{values.at(-1)}</div><div className="text-[9px] text-muted">{assessment.confidence}% confidence</div></div>
        </div>
        <TrendChart values={values} color={details.color} />
        <div className="mt-1 flex justify-between text-[8px] text-muted-2"><span>Earlier evidence</span><span>Latest</span></div>
      </div>
    </article>
  );
}

function TrendChart({ values, color }: { values: number[]; color: string }) {
  const width = 300; const height = 92; const pad = 8;
  const min = Math.min(...values) - 5; const max = Math.max(...values) + 5;
  const points = values.map((value, index) => {
    const x = pad + index * ((width - pad * 2) / (values.length - 1));
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

function trendValues(trend: FounderAssessment["trend"], seed: number): number[] {
  const base = 52 + (seed % 16);
  if (trend === "Improving") return [base, base + 4, base + 3, base + 10, base + 15];
  if (trend === "Declining") return [base + 14, base + 11, base + 12, base + 5, base];
  return [base + 2, base + 5, base + 3, base + 4, base + 3];
}
