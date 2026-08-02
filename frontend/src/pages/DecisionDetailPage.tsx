import {
  AlertTriangle,
  ArrowLeft,
  Building2,
  CheckCircle2,
  Clock3,
  ExternalLink,
  FileText,
  Loader2,
  Mail,
  MapPin,
  Minus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
  Users,
} from "lucide-react";
import { Link, useParams } from "react-router";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  fetchCandidateMemo,
  generateCandidateMemo,
  useCandidate,
} from "../api/candidates";
import { CandidateAvatar } from "../components/common/CandidateAvatar";
import { KeyMetricCard } from "../components/common/KeyMetricCard";
import { DecisionActionDock } from "../components/decision/DecisionActionDock";
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
  const { data: candidate, isLoading, error, refetch } = useCandidate(founderId);
  const [memoGenState, setMemoGenState] = useState<"idle" | "queued" | "error">("idle");
  const {
    data: memo,
    isLoading: memoLoading,
    refetch: refetchMemo,
  } = useQuery({
    queryKey: ["candidate-memo", founderId],
    queryFn: ({ signal }) => fetchCandidateMemo(founderId!, candidate?.opportunity?.id ?? "", signal),
    enabled: Boolean(founderId && candidate?.opportunity?.id),
    staleTime: 30_000,
    refetchInterval: memoGenState === "queued" ? 2_000 : false,
  });

  useEffect(() => {
    if (memo?.status === "succeeded" || memo?.status === "failed" || memo?.status === "degraded") {
      setMemoGenState("idle");
    }
  }, [memo?.status]);

  if (isLoading) return <div className="py-20 text-center text-sm text-muted">Loading investment evidence…</div>;
  if (error || !candidate) return <div className="py-20 text-center"><div className="text-sm font-bold">Decision candidate not found</div><Link to="/decisions" className="mt-3 inline-block text-xs font-bold text-accent">Back to decision queue</Link></div>;

  const profile = buildFounderProfile(candidate);
  const meta = createDecisionMeta(profile, candidate);

  const generateMemo = async () => {
    setMemoGenState("queued");
    try {
      if (!candidate?.opportunity?.id) return;
      await generateCandidateMemo(founderId!, candidate.opportunity.id);
      await refetchMemo();
    } catch {
      setMemoGenState("error");
    }
  };

  return (
    <div className="mx-auto max-w-[1240px] pb-28">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <Link
          to="/decisions"
          className="inline-flex items-center gap-2 text-xs font-bold text-muted transition-colors hover:text-ink"
        >
          <ArrowLeft className="h-4 w-4" /> Back to decision queue
        </Link>
        <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.1em] text-muted">
          <Clock3 className="h-3.5 w-3.5 text-amber-600" /> Decision due in {meta.deadline}
        </div>
      </div>

      <div className="grid items-start gap-5 lg:grid-cols-[270px_minmax(0,1fr)]">
        <FounderSidebar profile={profile} candidate={candidate} meta={meta} />

        <main className="min-w-0 space-y-5">
          <AiSummary profile={profile} meta={meta} />
          <DealMetrics profile={profile} meta={meta} />
          <AxisScreening profile={profile} />
          <InvestmentMemo
            memo={memo}
            memoLoading={memoLoading}
            memoGenState={memoGenState}
            onGenerate={generateMemo}
          />

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
        </main>
      </div>
      <DecisionActionDock
        candidateId={candidate.id}
        opportunityId={candidate.opportunity?.id ?? null}
        currentState={candidate.opportunity?.lifecycle_state ?? "No opportunity state"}
        onSaved={() => void refetch()}
      />
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
        <h1 className="text-[1.35rem] font-bold leading-tight tracking-[-0.025em]">{candidate.display_name ?? "Unknown founder"}</h1>
        <p className="mt-1 text-xs font-semibold text-ink-2">{profile.role}</p>
        <p className="text-xs text-muted">{profile.company}</p>

        <div className="mt-4 space-y-2.5 rounded-md bg-surface-2/75 p-3.5 text-xs leading-5 text-muted">
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
            <span key={tag} className="rounded bg-surface-2 px-2 py-1 text-[10px] font-semibold text-muted">
              {tag}
            </span>
          ))}
        </div>

        {candidate.profile?.deck_url && (
          <a
            href={candidate.profile.deck_url}
            target="_blank"
            rel="noreferrer"
            className="mt-5 flex w-full items-center justify-between rounded-md bg-[#e7eef9] px-3 py-2.5 text-xs font-bold text-[#5074a8] transition-all hover:-translate-y-0.5 hover:shadow-md"
          >
            <span className="flex min-w-0 items-center gap-2">
              <FileText className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">{candidate.profile.deck_stage ?? "Open pitch deck"}</span>
            </span>
            <ExternalLink className="h-3.5 w-3.5 shrink-0" />
          </a>
        )}

        <Link
          to={`/founders/${candidate.id}`}
          className="mt-5 flex w-full items-center justify-center rounded-md bg-white/75 py-2.5 text-xs font-bold text-ink-2 shadow-sm transition-all hover:-translate-y-0.5 hover:text-accent hover:shadow-md"
        >
          Open full founder profile
        </Link>

        <div className="mt-5 rounded-md bg-surface-2 p-3">
          <div className="data-label">Round context</div>
          <div className="mt-2 flex items-center justify-between text-xs">
            <span className="text-muted">Ask</span>
            <span className="font-bold">{meta.ask}</span>
          </div>
          <div className="mt-1.5 flex items-center justify-between text-xs">
            <span className="text-muted">Target ownership</span>
            <span className="font-bold">{meta.targetOwnership}</span>
          </div>
          <div className="mt-1.5 flex items-center justify-between text-xs">
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
    Proceed: { color: "#347c67", soft: "#e4f2ed", label: "Move forward" },
    Hold: { color: "#a96e2d", soft: "#fff1df", label: "Pause & verify" },
    Investigate: { color: "#5074a8", soft: "#e7eef9", label: "Diligence needed" },
  };
  const recommendation = styles[meta.recommendation];

  return (
    <section className="panel rounded-lg p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="eyebrow mb-2 flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5" /> AI investment summary
          </div>
          <h2 className="text-xl font-bold tracking-tight">{profile.company} at a glance</h2>
        </div>
        <div role="status" aria-label={`AI recommendation: ${meta.recommendation}`} className="inline-flex items-center gap-2 rounded-md px-2.5 py-2" style={{ backgroundColor: recommendation.soft }}>
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: recommendation.color }} />
          <span className="text-[10px] font-bold" style={{ color: recommendation.color }}>{meta.recommendation} · {recommendation.label}</span>
        </div>
      </div>
      <p className="mt-4 max-w-[900px] text-sm leading-7 text-ink-2">{meta.aiSummary}</p>
      <div className="mt-4 flex items-center gap-2 text-[10px] font-semibold leading-4 text-muted-2">
        <ShieldCheck className="h-3.5 w-3.5 text-accent" /> Generated from available evidence; key claims still require human verification.
      </div>
    </section>
  );
}

function DealMetrics({ profile, meta }: { profile: FounderProfile; meta: DecisionMeta }) {
  const founderAssessment = profile.assessments.find((assessment) => assessment.title === "Founder");

  return (
    <section className="grid gap-3 sm:grid-cols-3">
      <KeyMetricCard icon={Target} label="Thesis match" value={profile.thesisFit} suffix="%" detail="Fit with the active fund strategy" progress={profile.thesisFit} progressLabel={meta.recommendation} tone="purple" />
      <KeyMetricCard icon={Users} label="Founder signal" value={profile.founderScore} suffix="/100" detail="Traits, execution history and team-building signal" progress={profile.founderScore} progressLabel={founderAssessment?.rating ?? "Assessment pending"} tone="green" />
      <KeyMetricCard icon={ShieldCheck} label="Evidence quality" value={profile.evidence} suffix="%" detail="Confidence-weighted coverage of key claims" progress={profile.evidence} progressLabel={`${profile.claims.length} evidence records`} tone="blue" />
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
          <p className="supporting-text mt-1">Three independent scores — intentionally not averaged.</p>
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

function AxisCard({ assessment, score, values }: { assessment: FounderAssessment; score: number | null; values: number[] }) {
  const TrendIcon = assessment.trend === "Improving" ? TrendingUp : assessment.trend === "Declining" ? TrendingDown : Minus;
  const ratingVisual = assessment.rating === "Bullish"
    ? { color: "#347c67", soft: "#e4f2ed" }
    : assessment.rating === "Bearish"
      ? { color: "#b65d5d", soft: "#fbe8e9" }
      : assessment.rating === "Pending"
        ? { color: "#7d8999", soft: "#edf1f5" }
        : { color: "#a96e2d", soft: "#fff1df" };
  const tone = ratingVisual.color;
  const trendData = values.length ? values.slice(-5) : score == null ? [] : [score];
  const change = score != null && trendData.length ? score - trendData[0] : null;

  return (
    <article
      className="rounded-lg bg-white/55 p-4 shadow-[0_8px_22px_rgba(70,91,120,.05)]"
    >
      <div className="flex items-center justify-between gap-2">
        <div>
          <div className="text-[13px] font-bold">{assessment.title}</div>
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            <span className="inline-flex items-center gap-1 rounded px-2 py-1 text-[9px] font-bold uppercase tracking-wider" style={{ color: tone, backgroundColor: ratingVisual.soft }}>
              <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: tone }} />{assessment.rating}
            </span>
            <span className="inline-flex items-center gap-1 px-1 py-1 text-[9px] font-bold text-muted">
              <TrendIcon className="h-3 w-3" style={{ color: tone }} />{assessment.trend}
            </span>
          </div>
        </div>
        <div className="w-20 shrink-0 text-right">
          <span className="numeric text-xl font-bold leading-none" style={{ color: tone }}>{score ?? "—"}</span>
          <div role="meter" aria-label={`${assessment.title} axis score: ${score == null ? "pending" : `${score}%`}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={score ?? undefined} className="mt-2 h-1.5 overflow-hidden rounded-full" style={{ backgroundColor: ratingVisual.soft }}>
            <div className="h-full rounded-full" style={{ width: `${score ?? 0}%`, backgroundColor: tone }} />
          </div>
        </div>
      </div>
      <div className="mt-3 rounded-md bg-surface-2/70 px-3 pb-2 pt-3">
        <div className="flex items-center justify-between">
          <span className="data-label">Trend · last 5 updates</span>
          <span className="numeric text-[10px] font-bold" style={{ color: tone }}>
            {change == null ? "No measured change" : `${change > 0 ? "+" : ""}${change} pts`}
          </span>
        </div>
        {trendData.length ? <AxisTrendChart values={trendData} color={tone} label={`${assessment.title} ${assessment.trend} trend`} /> : <div className="flex h-20 items-center justify-center text-xs text-muted">No measured signal yet.</div>}
        <div className="flex justify-between text-[10px] text-muted-2">
          <span>Earlier evidence</span>
          <span>Latest</span>
        </div>
      </div>
      <p className="mt-3 text-xs leading-5 text-muted">{assessment.body}</p>
      <div className="mt-3 rounded bg-surface-2/70 px-2.5 py-2">
        <div className="flex items-center justify-between text-[9px] font-bold uppercase tracking-wider text-muted-2"><span>Evidence confidence</span><span className="numeric" style={{ color: tone }}>{assessment.confidence}%</span></div>
        <div className="mt-1.5 h-1.5 overflow-hidden rounded-full" style={{ backgroundColor: ratingVisual.soft }}><div className="h-full rounded-full" style={{ width: `${assessment.confidence}%`, backgroundColor: tone }} /></div>
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

function InvestmentMemo({
  memo,
  memoLoading,
  memoGenState,
  onGenerate,
}: {
  memo: import("../api/candidates").CandidateMemo | null | undefined;
  memoLoading: boolean;
  memoGenState: "idle" | "queued" | "error";
  onGenerate: () => void;
}) {
  const hasMemo = memo?.status === "succeeded" && memo.sections.length > 0;
  const hasDraft = Boolean(memo && memo.status !== "missing" && memo.status !== "pending" && memo.sections.length > 0);
  const memoStatus = memo?.status === "degraded" ? "Degraded draft · not decision-ready" : memo?.status === "failed" ? "Generation failed · not decision-ready" : memo?.status === "pending" ? "Generation pending" : null;
  const renderableMemo = memo && (hasMemo || hasDraft) ? memo : null;

  return (
    <section className="panel rounded-lg p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-gradient-to-r from-[#edf3fb] to-[#eef6f3] px-4 py-3.5">
        <div>
          <div className="eyebrow mb-2 flex items-center gap-1.5"><FileText className="h-3.5 w-3.5" /> Investment memo</div>
          <h2 className="text-lg font-bold">Detailed IC report</h2>
        </div>
        <div className="flex items-center gap-2">
          {(hasMemo || hasDraft) && (
            <span className="status-pill bg-surface-2 text-muted">
              {hasMemo ? `${memo.generation_mode === "agent" ? "AI generated" : "Validated memo"} · ${memo.model_version ?? "unknown"}` : memoStatus}
            </span>
          )}
          {!hasMemo && !memoLoading && memo?.status !== "pending" && (
            <button
              onClick={onGenerate}
              disabled={memoGenState === "queued"}
              className="inline-flex items-center gap-1.5 rounded-md bg-accent px-3 py-2 text-[10px] font-bold text-white disabled:opacity-60"
            >
              {memoGenState === "queued" ? (
                <><Loader2 className="h-3 w-3 animate-spin" /> Generating…</>
              ) : memoGenState === "error" ? (
                <><RefreshCw className="h-3 w-3" /> Retry</>
              ) : (
                <><Sparkles className="h-3.5 w-3.5" /> Generate memo</>
              )}
            </button>
          )}
        </div>
      </div>

      {memoLoading && (
        <div className="mt-5 flex items-center justify-center gap-2 py-10 text-xs text-muted">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading memo…
        </div>
      )}

      {!memoLoading && memoStatus && (
        <div role="alert" className="mt-5 rounded-md border border-warn/25 bg-[#fff8ed] p-4 text-xs text-[#8d5e2b]">
          {memoStatus}. It cannot advance the opportunity to memo-ready until a validated memo succeeds.
        </div>
      )}

      {!memoLoading && renderableMemo && (
        <div className="mt-5 grid gap-x-7 gap-y-6 xl:grid-cols-2">
          {renderableMemo.sections.map((section) => (
            <div key={section.title}>
              <MemoHeading icon={FileText} title={section.title} />
              <p className="mt-3 text-xs leading-6 text-ink-2">{section.text}</p>
              {section.evidence_ids.length > 0 && (
                <p className="mt-2 text-[10px] text-muted-2">
                  {section.evidence_ids.length} evidence reference{section.evidence_ids.length === 1 ? "" : "s"}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {!memoLoading && !hasMemo && memo?.status !== "pending" && memoGenState === "idle" && (
        <div className="mt-5 rounded-md bg-surface-2 p-4 text-center text-xs text-muted">
          No investment memo has been generated yet. Click "Generate memo" to create one from the available evidence.
        </div>
      )}

      {!memoLoading && !hasMemo && memo?.status !== "pending" && memoGenState === "queued" && (
        <div className="mt-5 rounded-md bg-surface-2 p-4 text-center text-xs text-muted">
          Memo generation has been queued. It will appear here once complete.
        </div>
      )}

      {!memoLoading && !hasMemo && memo?.status !== "pending" && memoGenState === "error" && (
        <div className="mt-5 rounded-md bg-[#fff1df] p-4 text-center text-xs text-[#a96e2d]">
          Memo generation failed. Please retry.
        </div>
      )}
    </section>
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
        <div><div className="data-label">{eyebrow}</div><h2 className="mt-0.5 text-[15px] font-bold">{title}</h2></div>
      </div>
      <ul className="mt-4 space-y-3">
        {items.map((item, index) => (
          <li key={item} className="flex gap-2.5 text-xs leading-5 text-ink-2">
            <span className={`numeric mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded text-[10px] font-bold ${colors}`}>{index + 1}</span>
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
        <span className="numeric text-[11px] font-bold text-muted">{profile.claims.length} claims reviewed</span>
      </div>
      <div className="mt-4 space-y-2">
        {profile.claims.map((claim) => {
          const supported = claim.status === "Supported";
          return (
            <div key={claim.claim} className="grid gap-3 rounded-md bg-surface-2/75 px-4 py-3 sm:grid-cols-[1fr_100px_120px] sm:items-center">
              <div className="text-xs font-semibold leading-5 text-ink-2">{claim.claim}</div>
              <div className="text-[11px] text-muted">Trust <span className="numeric font-bold text-ink">{claim.trust}%</span></div>
              <span className={`status-pill w-fit ${supported ? "bg-[#e4f2ed] text-[#347c67]" : "bg-[#fff1df] text-[#a96e2d]"}`}>
                {claim.status}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function SidebarRow({ icon: Icon, value }: { icon: React.ElementType; value: string }) {
  return <div className="flex items-start gap-2"><Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-2" /><span className="break-all">{value}</span></div>;
}

function SmallMetric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md bg-surface-2 p-3"><div className="numeric text-lg font-bold leading-none">{value}</div><div className="mt-1 text-[10px] text-muted">{label}</div></div>;
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
