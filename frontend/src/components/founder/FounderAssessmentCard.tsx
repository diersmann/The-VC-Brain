import { CircleGauge, Globe2, Lightbulb, TrendingDown, TrendingUp, UserRound } from "lucide-react";
import type { FounderAssessment, FounderProfile } from "../../types/profile";
import { confidenceViewModel, ratingViewModel, trendViewModel } from "../../data/displayMetrics";

const axisDetails = {
  Founder: { icon: UserRound, description: "Who they are, their traits and track record.", color: "#6f8db7", soft: "bg-[#e7eef9] text-[#5074a8]", checks: ["Technical capability", "Execution history", "Team building"] },
  Market: { icon: Globe2, description: "Market sizing, competitors and SWOT.", color: "#4f9b84", soft: "bg-[#e4f2ed] text-[#347c67]", checks: ["Market size", "Competitive landscape", "Tailwinds & risks"] },
  "Idea × Market": { icon: Lightbulb, description: "Does the idea survive scrutiny, or can the team pivot?", color: "#8b6db6", soft: "bg-[#eee8f8] text-[#7656a5]", checks: ["Problem strength", "Solution fit", "Pivot capacity"] },
};

export function FounderAssessmentCard({ assessment, profile, history }: { assessment: FounderAssessment; profile: FounderProfile; history: number[] }) {
  const details = axisDetails[assessment.title];
  const Icon = details.icon;
  const values = history.length ? history.slice(-5) : assessment.score == null ? [] : [assessment.score];
  const ratingVisual = ratingViewModel(assessment.rating);
  const trend = trendViewModel(assessment.trend);
  const confidence = confidenceViewModel(assessment.confidence, "Assessment");
  const TrendIcon = trend.direction === "down" ? TrendingDown : trend.direction === "up" ? TrendingUp : CircleGauge;
  const explanation = axisExplanation(assessment.title, profile);

  return <article className="panel overflow-hidden rounded-lg"><div className="p-5"><div className="flex items-start justify-between gap-3"><span className={`flex h-10 w-10 items-center justify-center rounded-md ${details.soft}`}><Icon className="h-5 w-5" /></span><span role="img" aria-label={`Rating: ${ratingVisual.label}. ${ratingVisual.explanation}`} className="rounded-full px-2.5 py-1 text-[10px] font-bold" style={{ backgroundColor: ratingVisual.soft, color: ratingVisual.color }}>{ratingVisual.label}</span></div><h3 className="mt-4 text-base font-bold">{assessment.title}</h3><p className="mt-1 text-xs leading-5 text-muted">{details.description}</p><div className="mt-4 rounded-md bg-surface-2/80 p-3 shadow-inner shadow-white/80"><div className="data-label">Why this rating</div><p className="mt-1.5 text-xs font-medium leading-5 text-ink-2">{assessment.body}</p></div><div className="mt-4 space-y-3 rounded-md bg-white/55 p-3"><InsightRow kind="support" label="Supporting evidence" text={explanation.support} meta={explanation.supportMeta} /><InsightRow kind="risk" label="Counter-evidence / risk" text={explanation.risk} /><InsightRow kind="unknown" label="Still unknown" text={explanation.unknown} /></div></div><div className="bg-gradient-to-br from-surface-2 to-[#edf4f4] px-5 pb-4 pt-4"><div className="mb-2 flex items-center justify-between"><div><div className="data-label">Trend · last 5 updates</div><div role="img" aria-label={`Trend: ${trend.label}. ${trend.explanation}`} className="mt-1 flex items-center gap-1.5 text-xs font-bold" style={{ color: details.color }}><TrendIcon className="h-3.5 w-3.5" />{trend.label}</div></div><div className="text-right"><div className="numeric text-xl font-bold leading-none">{values.at(-1) ?? "—"}</div><div className="mt-1 text-[10px] text-muted">Current signal</div></div></div>{values.length ? <TrendChart values={values} color={details.color} /> : <div className="flex h-[92px] items-center justify-center text-xs text-muted">No measured signal yet.</div>}<div className="mt-1 flex justify-between text-[10px] text-muted-2"><span>Earlier evidence</span><span>Latest</span></div><div className="mt-3 rounded-md bg-white/55 p-3"><div className="data-label mb-1.5 flex items-center justify-between"><span>Assessment confidence</span><span className="numeric">{confidence.label}</span></div><div className="h-1.5 bg-surface-3" role="progressbar" aria-label={`${assessment.title} confidence: ${confidence.label}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={confidence.percent ?? undefined} aria-valuetext={confidence.explanation}><div className="h-full" style={{ width: `${confidence.percent ?? 0}%`, backgroundColor: details.color }} /></div><p className="mt-2 text-[10px] leading-4 text-muted">{confidence.explanation} Each point is a versioned Memory update based on new evidence or an investor correction.</p></div></div></article>;
}

function InsightRow({ kind, label, text, meta }: { kind: "support" | "risk" | "unknown"; label: string; text: string; meta?: string }) {
  const styles = kind === "support" ? { dot: "bg-success", label: "text-success" } : kind === "risk" ? { dot: "bg-danger", label: "text-danger" } : { dot: "bg-warn", label: "text-warn" };
  return <div className="flex gap-2.5"><span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${styles.dot}`} /><div><div className={`text-[10px] font-bold uppercase tracking-wider ${styles.label}`}>{label}</div><p className="mt-1 text-[11px] leading-[1.55] text-ink-2">{text}</p>{meta && <div className="numeric mt-1 text-[10px] text-muted">{meta}</div>}</div></div>;
}

function axisExplanation(axis: FounderAssessment["title"], profile: FounderProfile) {
  const strongestClaim = [...profile.claims].sort((a, b) => b.trust - a.trust)[0];
  const latestEvent = profile.events[0];
  if (axis === "Founder") {
    const trust = latestEvent?.trust ?? profile.sourceConfidence;
    return { support: latestEvent?.body ?? profile.scoreHint, supportMeta: `${latestEvent?.type ?? "Track record"} · Trust ${trust == null ? "Not scored" : `${trust}%`}`, risk: profile.gaps.at(-1) ?? "Team-building evidence remains limited.", unknown: "Performance under sustained fundraising and scaling pressure." };
  }
  if (axis === "Market") {
    const marketCoverage = profile.coverage.at(-1);
    const trust = strongestClaim?.trust ?? profile.sourceConfidence;
    return { support: `${profile.sector} demand is supported by: ${strongestClaim?.claim ?? profile.signal}.`, supportMeta: `${strongestClaim?.status ?? "Supported"} · Trust ${trust == null ? "Not scored" : `${trust}%`}`, risk: profile.gaps[1] ?? profile.gaps[0] ?? "Competitive response needs deeper review.", unknown: `${marketCoverage?.label ?? "Bottom-up market size"} is only ${marketCoverage?.value ?? 50}% evidenced.` };
  }
  const trust = profile.claims[1]?.trust ?? profile.sourceConfidence;
  return { support: profile.signal, supportMeta: `${profile.claims[1]?.source ?? "Product and traction evidence"} · Trust ${trust == null ? "Not scored" : `${trust}%`}`, risk: profile.gaps[0] ?? "Repeatable customer demand has not been independently verified.", unknown: "Whether the current wedge scales without a material product pivot." };
}

function TrendChart({ values, color }: { values: number[]; color: string }) {
  const width = 300; const height = 92; const pad = 8;
  const min = Math.min(...values) - 5; const max = Math.max(...values) + 5;
  const points = values.map((value, index) => { const x = values.length === 1 ? width / 2 : pad + index * ((width - pad * 2) / (values.length - 1)); const y = height - pad - ((value - min) / Math.max(1, max - min)) * (height - pad * 2); return { x, y, value }; });
  const line = points.map((point) => `${point.x},${point.y}`).join(" ");
  const area = `${pad},${height - pad} ${line} ${width - pad},${height - pad}`;
  return <svg viewBox={`0 0 ${width} ${height}`} className="h-[92px] w-full" role="img" aria-label={`Trend values ${values.join(", ")}`}><defs><linearGradient id={`area-${color.replace("#", "")}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={color} stopOpacity=".24" /><stop offset="100%" stopColor={color} stopOpacity="0" /></linearGradient></defs>{[25, 50, 75].map((y) => <line key={y} x1="8" y1={y} x2="292" y2={y} stroke="#dfe6ef" strokeWidth="1" strokeDasharray="3 4" />)}<polygon points={area} fill={`url(#area-${color.replace("#", "")})`} /><polyline points={line} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />{points.map((point, index) => <circle key={index} cx={point.x} cy={point.y} r={index === points.length - 1 ? 4 : 2.5} fill="white" stroke={color} strokeWidth="2" />)}</svg>;
}
