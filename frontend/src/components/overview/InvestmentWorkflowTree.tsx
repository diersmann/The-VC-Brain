import {
  BrainCircuit,
  Compass,
  DatabaseZap,
  FileCheck2,
  Inbox,
  RefreshCw,
  Scale,
  Target,
} from "lucide-react";
import type { LifecycleContract } from "../../api/lifecycle";

type WorkflowCounts = {
  inbound: number;
  outbound: number;
  total: number;
  scored: number;
  pending: number;
  highSignal: number;
};

type InvestmentWorkflowTreeProps = {
  thesisName: string;
  thesisVersion?: string;
  counts: WorkflowCounts;
  lifecycle?: LifecycleContract;
  onNavigate: (path: string) => void;
};

const nodeTones = {
  blue: "bg-gradient-to-br from-[#e7eef9] to-[#f4f7fc] text-[#5074a8]",
  purple: "bg-gradient-to-br from-[#eee8f8] to-[#f8f5fc] text-[#7656a5]",
  green: "bg-gradient-to-br from-[#e4f2ed] to-[#f2f8f6] text-[#347c67]",
  amber: "bg-gradient-to-br from-[#fff1df] to-[#fff9f0] text-[#a96e2d]",
  slate: "bg-gradient-to-br from-[#e9eef4] to-[#f7f9fc] text-[#586b84]",
} as const;

export function InvestmentWorkflowTree({ thesisName, thesisVersion, counts, lifecycle, onNavigate }: InvestmentWorkflowTreeProps) {
  if (!lifecycle) {
    return <section className="panel mb-6 rounded-lg p-5 text-sm text-muted" role="status">Workflow contract unavailable.</section>;
  }
  const label = (key: string) => lifecycle.stages.find((stage) => stage.key === key)?.label ?? key;

  return (
    <section className="panel mb-6 overflow-hidden rounded-lg p-5 md:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="eyebrow mb-2">Unified deal lifecycle</div>
          <h2 className="text-lg font-bold tracking-[-0.02em]">Investment workflow</h2>
          <p className="supporting-text mt-1">Live opportunities move from thesis and sourcing to evidence-backed human decisions.</p>
        </div>
        <div className="flex items-center gap-4 text-[11px] font-semibold text-muted">
          <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-success" /> Live database counts</span>
          <span className="hidden items-center gap-1.5 sm:inline-flex"><RefreshCw className="h-3.5 w-3.5 text-accent" /> Every stage writes to Memory</span>
        </div>
      </div>

      <div className="mt-6">
        <div className="mx-auto max-w-[260px]">
          <WorkflowNode
            icon={Target}
            step="01 · Strategy"
            title="Investment thesis"
            value={thesisName}
            detail={thesisVersion ? `${thesisVersion} · active criteria` : "Configure active criteria"}
            tone="blue"
            onClick={() => onNavigate("/thesis")}
          />
        </div>

        <SourceSplitConnector />

        <div className="mx-auto grid max-w-[720px] grid-cols-2 gap-3 sm:gap-5">
          <WorkflowNode
            compact
            icon={Inbox}
            step="02A · Inbound"
            title="Founder applications"
            value={`${counts.inbound} records`}
            detail="Company + pitch deck"
            tone="purple"
            onClick={() => onNavigate("/inbound")}
          />
          <WorkflowNode
            compact
            icon={Compass}
            step="02B · Outbound"
            title="Public discovery"
            value={`${counts.outbound} profiles`}
            detail="Signals + identity evidence"
            tone="green"
            onClick={() => onNavigate("/sourcing")}
          />
        </div>

        <SourceMergeConnector />

        <div className="hidden grid-cols-[minmax(0,1fr)_36px_minmax(0,1fr)_36px_minmax(0,1fr)_36px_minmax(0,1fr)] items-center gap-2 xl:grid">
          <WorkflowNode
            icon={DatabaseZap}
            step="03 · Converge"
            title="Opportunity pipeline"
            value={`${counts.total} opportunities`}
            detail={`${label("received")} · ${label("triage")} · identity resolution`}
            tone="slate"
            onClick={() => onNavigate("/investigated")}
          />

          <ArrowConnector label="assess" />

          <WorkflowNode
            icon={BrainCircuit}
            step="04 · Intelligence"
            title={`${label("screening")} & ${label("diligence")}`}
            value={`${counts.scored} scored`}
            detail={`${label("investigating")} · Founder · Market · Idea × Market · ${counts.pending} pending`}
            tone="green"
            onClick={() => onNavigate("/investigated")}
          />

          <ArrowConnector label="memo" />

          <WorkflowNode
            icon={FileCheck2}
            step="05 · IC review"
            title={`${label("memo_ready")} & decision`}
            value={`${counts.highSignal} high signal`}
            detail="Evidence memo + human approval"
            tone="amber"
            onClick={() => onNavigate("/decisions")}
          />

          <ArrowConnector label="feedback" />

          <WorkflowNode
            icon={Scale}
            step="06 · Memory"
            title={`${label("approved")} / ${label("closed")} feedback`}
            value={`${counts.scored} snapshots`}
            detail="No separate Memory workspace yet"
            tone="blue"
          />
        </div>

        <div className="mx-auto max-w-[440px] xl:hidden">
          <WorkflowNode
            icon={DatabaseZap}
            step="03 · Converge"
            title="Opportunity pipeline"
            value={`${counts.total} opportunities`}
            detail={`${label("received")} · ${label("triage")} · identity resolution`}
            tone="slate"
            onClick={() => onNavigate("/investigated")}
          />
          <VerticalArrowConnector label="assess" />
          <WorkflowNode
            icon={BrainCircuit}
            step="04 · Intelligence"
            title={`${label("screening")} & ${label("diligence")}`}
            value={`${counts.scored} scored`}
            detail={`${label("investigating")} · Founder · Market · Idea × Market · ${counts.pending} pending`}
            tone="green"
            onClick={() => onNavigate("/investigated")}
          />
          <VerticalArrowConnector label="memo" />
          <WorkflowNode
            icon={FileCheck2}
            step="05 · IC review"
            title={`${label("memo_ready")} & decision`}
            value={`${counts.highSignal} high signal`}
            detail="Evidence memo + human approval"
            tone="amber"
            onClick={() => onNavigate("/decisions")}
          />
          <VerticalArrowConnector label="feedback" />
          <WorkflowNode
            icon={Scale}
            step="06 · Memory"
            title={`${label("approved")} / ${label("closed")} feedback`}
            value={`${counts.scored} snapshots`}
            detail="No separate Memory workspace yet"
            tone="blue"
          />
        </div>
      </div>

      <div className="mt-1 flex items-center justify-between gap-3 rounded-md bg-white/55 px-3 py-2.5 text-[11px] text-muted">
        <span>Click any node to open that workspace.</span>
        <span className="hidden sm:inline">The full lifecycle now stays inside the page at every screen size.</span>
      </div>
    </section>
  );
}

function WorkflowNode({
  icon: Icon,
  step,
  title,
  value,
  detail,
  tone,
  compact = false,
  onClick,
}: {
  icon: React.ElementType;
  step: string;
  title: string;
  value: string;
  detail: string;
  tone: keyof typeof nodeTones;
  compact?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!onClick}
      aria-disabled={!onClick}
      className={`${compact ? "min-h-[104px]" : "min-h-[132px]"} group relative w-full overflow-hidden rounded-lg p-4 text-left shadow-[0_10px_28px_rgba(70,91,120,.08)] transition duration-200 ${onClick ? "hover:-translate-y-1 hover:shadow-[0_16px_36px_rgba(70,91,120,.14)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent" : "cursor-not-allowed opacity-75"} ${nodeTones[tone]}`}
    >
      <span className="pointer-events-none absolute -right-5 -top-5 h-16 w-16 rounded-full bg-white/55 blur-xl" />
      <div className="relative flex items-start justify-between gap-2">
        <div className="data-label opacity-80">{step}</div>
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-white/65 shadow-sm">
          <Icon className="h-3.5 w-3.5" />
        </span>
      </div>
      <div className="relative mt-2 text-[13px] font-bold text-ink">{title}</div>
      <div className={`${compact ? "mt-1 text-[15px]" : "mt-3 text-lg"} numeric relative font-bold leading-tight`}>{value}</div>
      <div className="relative mt-1.5 text-[10px] font-medium leading-4 text-muted">{detail}</div>
    </button>
  );
}

function SourceSplitConnector() {
  return (
    <svg aria-hidden="true" viewBox="0 0 720 58" preserveAspectRatio="none" className="mx-auto h-12 w-full max-w-[720px] overflow-visible sm:h-[58px]">
      <path d="M360 0 V22 H180 V56" fill="none" stroke="#b8c6d8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M360 22 H540 V56" fill="none" stroke="#b8c6d8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="360" cy="22" r="4" fill="#7186a4" />
      <circle cx="180" cy="56" r="3" fill="#7656a5" />
      <circle cx="540" cy="56" r="3" fill="#347c67" />
    </svg>
  );
}

function SourceMergeConnector() {
  return (
    <svg aria-hidden="true" viewBox="0 0 720 58" preserveAspectRatio="none" className="mx-auto h-12 w-full max-w-[720px] overflow-visible sm:h-[58px]">
      <path d="M180 2 V36 H360 V58" fill="none" stroke="#b8c6d8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M540 2 V36 H360" fill="none" stroke="#b8c6d8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="180" cy="2" r="3" fill="#7656a5" />
      <circle cx="540" cy="2" r="3" fill="#347c67" />
      <circle cx="360" cy="36" r="4" fill="#7186a4" />
    </svg>
  );
}

function ArrowConnector({ label }: { label: string }) {
  return (
    <div className="flex w-9 flex-col items-center gap-2">
      <span className="data-label normal-case tracking-normal">{label}</span>
      <svg aria-hidden="true" viewBox="0 0 36 12" className="h-3 w-9 overflow-visible">
        <path d="M1 6 H31" fill="none" stroke="#b8c6d8" strokeWidth="2" strokeLinecap="round" />
        <path d="m27 2 5 4-5 4" fill="none" stroke="#7186a4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

function VerticalArrowConnector({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center py-2">
      <span className="data-label normal-case tracking-normal">{label}</span>
      <svg aria-hidden="true" viewBox="0 0 12 34" className="mt-1 h-[34px] w-3 overflow-visible">
        <path d="M6 1 V29" fill="none" stroke="#b8c6d8" strokeWidth="2" strokeLinecap="round" />
        <path d="m2 25 4 5 4-5" fill="none" stroke="#7186a4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}
