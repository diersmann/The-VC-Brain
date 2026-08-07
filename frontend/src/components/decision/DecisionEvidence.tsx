import { Minus, TrendingDown, TrendingUp } from "lucide-react";
import type { FounderAssessment, FounderProfile } from "../../types/profile";
import { confidenceViewModel, ratingViewModel, scoreViewModel, trendViewModel } from "../../data/displayMetrics";

export function AxisScreening({ profile }: { profile: FounderProfile }) {
  return <section className="panel rounded-lg p-5 sm:p-6"><div className="flex flex-wrap items-end justify-between gap-3"><div><div className="eyebrow mb-2">Decision quality</div><h2 className="text-lg font-bold">Multi-axis screening</h2><p className="supporting-text mt-1">Three independent scores — intentionally not averaged.</p></div></div><div className="mt-5 grid gap-3 xl:grid-cols-3">{profile.assessments.map((assessment) => <AxisCard key={assessment.title} assessment={assessment} score={assessment.score} values={profile.axisTrendHistory[assessment.title]} />)}</div></section>;
}

function AxisCard({ assessment, score, values }: { assessment: FounderAssessment; score: number | null; values: number[] }) {
  const trend = trendViewModel(assessment.trend);
  const TrendIcon = trend.direction === "up" ? TrendingUp : trend.direction === "down" ? TrendingDown : Minus;
  const ratingVisual = ratingViewModel(assessment.rating);
  const scoreVisual = scoreViewModel(score, "decision");
  const confidence = confidenceViewModel(assessment.confidence, "Assessment");
  const tone = ratingVisual.color;
  const trendData = values.length ? values.slice(-5) : score == null ? [] : [score];
  const change = score != null && trendData.length ? score - trendData[0] : null;
  return <article className="rounded-lg bg-white/55 p-4 shadow-[0_8px_22px_rgba(70,91,120,.05)]"><div className="flex items-center justify-between gap-2"><div><div className="text-[13px] font-bold">{assessment.title}</div><div className="mt-2 flex flex-wrap items-center gap-1.5"><span role="img" aria-label={`Rating: ${ratingVisual.label}. ${ratingVisual.explanation}`} className="inline-flex items-center gap-1 rounded px-2 py-1 text-[9px] font-bold uppercase tracking-wider" style={{ color: tone, backgroundColor: ratingVisual.soft }}><span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: tone }} />{ratingVisual.label}</span><span role="img" aria-label={`Trend: ${trend.label}. ${trend.explanation}`} className="inline-flex items-center gap-1 px-1 py-1 text-[9px] font-bold text-muted"><TrendIcon className="h-3 w-3" style={{ color: tone }} />{trend.label}</span></div></div><div className="w-20 shrink-0 text-right"><span className="numeric text-xl font-bold leading-none" style={{ color: tone }}>{scoreVisual.percent == null ? "—" : scoreVisual.percent}</span><div role="meter" aria-label={`${assessment.title} axis score: ${scoreVisual.percent == null ? "pending" : `${scoreVisual.percent}%`}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={scoreVisual.percent ?? undefined} aria-valuetext={scoreVisual.explanation} className="mt-2 h-1.5 overflow-hidden rounded-full" style={{ backgroundColor: ratingVisual.soft }}><div className="h-full rounded-full" style={{ width: `${scoreVisual.percent ?? 0}%`, backgroundColor: tone }} /></div></div></div><div className="mt-3 rounded-md bg-surface-2/70 px-3 pb-2 pt-3"><div className="flex items-center justify-between"><span className="data-label">Trend · last 5 updates</span><span className="numeric text-[10px] font-bold" style={{ color: tone }}>{change == null ? "No measured change" : `${change > 0 ? "+" : ""}${change} pts`}</span></div>{trendData.length ? <AxisTrendChart values={trendData} color={tone} label={`${assessment.title} ${trend.label} trend`} /> : <div className="flex h-20 items-center justify-center text-xs text-muted">No measured signal yet.</div>}<div className="flex justify-between text-[10px] text-muted-2"><span>Earlier evidence</span><span>Latest</span></div></div><p className="mt-3 text-xs leading-5 text-muted">{assessment.body}</p><div className="mt-3 rounded bg-surface-2/70 px-2.5 py-2"><div className="flex items-center justify-between text-[9px] font-bold uppercase tracking-wider text-muted-2"><span>Evidence confidence</span><span className="numeric" style={{ color: tone }}>{confidence.label}</span></div><div className="mt-1.5 h-1.5 overflow-hidden rounded-full" style={{ backgroundColor: ratingVisual.soft }} role="progressbar" aria-label={`${assessment.title} confidence: ${confidence.label}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={confidence.percent ?? undefined} aria-valuetext={confidence.explanation}><div className="h-full rounded-full" style={{ width: `${confidence.percent ?? 0}%`, backgroundColor: tone }} /></div></div></article>;
}

function AxisTrendChart({ values, color, label }: { values: number[]; color: string; label: string }) {
  const width = 260;
  const height = 72;
  const padding = 7;
  const minimum = Math.min(...values) - 5;
  const maximum = Math.max(...values) + 5;
  const points = values.map((value, index) => ({ x: values.length === 1 ? width / 2 : padding + index * ((width - padding * 2) / (values.length - 1)), y: height - padding - ((value - minimum) / Math.max(1, maximum - minimum)) * (height - padding * 2) }));
  const line = points.map((point) => `${point.x},${point.y}`).join(" ");
  const area = `${padding},${height - padding} ${line} ${width - padding},${height - padding}`;
  const gradientId = `decision-trend-${label.replace(/[^a-z0-9]/gi, "-").toLowerCase()}`;
  return <svg viewBox={`0 0 ${width} ${height}`} className="mt-1 h-[72px] w-full" role="img" aria-label={`${label}: ${values.join(", ")}`}><defs><linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={color} stopOpacity="0.22" /><stop offset="100%" stopColor={color} stopOpacity="0" /></linearGradient></defs>{[22, 44, 66].map((y) => <line key={y} x1={padding} y1={y} x2={width - padding} y2={y} stroke="#dfe6ef" strokeWidth="1" strokeDasharray="3 4" />)}<polygon points={area} fill={`url(#${gradientId})`} /><polyline points={line} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />{points.map((point, index) => <circle key={`${point.x}-${point.y}`} cx={point.x} cy={point.y} r={index === points.length - 1 ? 3.5 : 2.25} fill="white" stroke={color} strokeWidth="2" />)}</svg>;
}
