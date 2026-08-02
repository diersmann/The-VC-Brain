import { useState } from "react";
import {
  ArrowUpRight,
  Building2,
  CheckCircle2,
  ExternalLink,
  Lightbulb,
  MapPin,
  Send,
  ShieldCheck,
  Sparkles,
  Store,
  UserRound,
  X,
} from "lucide-react";

import { formatPredicate } from "../../data/candidateProfile";
import { safeExternalUrl } from "../../data/candidateLinks";
import { scorePercent, scoreVisual } from "../../data/displayMetrics";
import { recordCandidateFeedback } from "../../api/candidates";
import type { Candidate } from "../../types/candidate";
import { CandidateAvatar } from "../common/CandidateAvatar";

interface Props {
  candidate: Candidate;
  onViewFounder: () => void;
  onOutreach?: () => void;
}

const percentage = (value: number | null | undefined) =>
  scorePercent(value) == null ? "—" : `${scorePercent(value)}%`;

export function CandidateCard({ candidate, onViewFounder, onOutreach }: Props) {
  const [dismissed, setDismissed] = useState(false);
  const [dismissReason, setDismissReason] = useState("");
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackState, setFeedbackState] = useState<"idle" | "saving" | "error">("idle");
  if (dismissed) return null;

  const profile = candidate.profile;
  const websiteUrl = safeExternalUrl(profile?.website);
  const source = Object.keys(candidate.handles ?? {})[0] ?? candidate.origin ?? "database";
  const handle = Object.values(candidate.handles ?? {})[0];
  const evidence = candidate.scores?.evidence_confidence;
  const originTone = candidate.origin === "inbound"
    ? "bg-[#ece9fb] text-[#7059a6]"
    : candidate.origin === "outbound"
      ? "bg-[#e4f3ee] text-[#327d68]"
      : "bg-accent-soft text-accent";

  return (
    <article
      onClick={onViewFounder}
      className="panel group cursor-pointer rounded-lg p-5 transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_18px_45px_rgba(65,90,125,.13)]"
    >
      <div className="flex items-start gap-3">
        <CandidateAvatar
          name={candidate.display_name}
          avatarUrl={candidate.avatar_url}
          className="h-12 w-12 rounded-lg bg-gradient-to-br from-[#dce6f2] to-[#c6d3e3] text-sm font-bold text-accent ring-2 ring-white shadow-sm"
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate text-[15px] font-bold leading-tight">{candidate.display_name ?? candidate.stable_id}</h3>
            {candidate.consent_state === "granted" && <CheckCircle2 className="h-3.5 w-3.5 text-success" />}
            <span className={`status-pill ${originTone}`}>
              {candidate.origin === "inbound" ? "Inbound" : candidate.origin === "outbound" ? "Outbound" : "Discovered"}
            </span>
          </div>
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted">
            <span className="inline-flex items-center gap-1 font-medium text-ink-2">
              <Building2 className="h-3 w-3 text-[#6f8db7]" />
              {profile?.company?.replace(/^@/, "") || "Company not disclosed"}
            </span>
            <span className="inline-flex items-center gap-1">
              <MapPin className="h-3 w-3 text-[#c27a5b]" />
              {profile?.location || "Location not disclosed"}
            </span>
          </div>
          <div className="mt-1 text-[10px] text-muted">
            {formatPredicate(source)}{handle ? ` · ${handle}` : ""}
          </div>
        </div>
        <button
          aria-label="Dismiss"
          onClick={(event) => {
            event.stopPropagation();
            setFeedbackOpen(true);
          }}
          className="rounded-md p-1.5 text-muted-2 hover:bg-surface-2"
        >
          <X className="h-4 w-4" />
          <span className="sr-only">Dismiss</span>
        </button>
      </div>

      <div className="my-4 rounded-md bg-gradient-to-br from-surface-2 to-[#edf2f8] p-3.5">
        <div className="flex gap-2">
          <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
          <div>
            <div className="data-label">Evidence summary</div>
            <p className="mt-1.5 line-clamp-3 text-[13px] leading-5 text-ink-2">
              {profile?.summary || `Public activity was collected from ${formatPredicate(source)}, but a verified founder summary is still pending.`}
            </p>
          </div>
        </div>
      </div>

      {!candidate.scores && <div className="mb-2 text-[11px] font-semibold text-warn">No scores yet</div>}
      <div className="grid grid-cols-3 gap-2">
        <Metric icon={UserRound} label="Founder" value={candidate.scores?.founder ?? candidate.scores?.raw?.founder} />
        <Metric icon={Store} label="Market" value={candidate.scores?.market ?? candidate.scores?.raw?.market} />
        <Metric icon={Lightbulb} label="Idea × Market" value={candidate.scores?.idea_market ?? candidate.scores?.raw?.idea_market} />
      </div>

      <EvidenceBar value={evidence} />

      <div className="mt-3 flex flex-wrap items-center gap-2 text-[10px] font-semibold text-muted">
        <span className="rounded-full bg-white/80 px-2.5 py-1">
          {profile?.observation_count ?? 0} observations
        </span>
        <span className="rounded-full bg-white/80 px-2.5 py-1">
          {profile?.source_types.length ?? 0} source types
        </span>
        <span className="rounded-full bg-white/80 px-2.5 py-1">
          {Math.round((profile?.completeness ?? 0) * 100)}% complete
        </span>
      </div>

      <div className="mt-4 flex flex-wrap gap-1.5">
        {(profile?.source_types ?? Object.keys(candidate.handles ?? {})).map((tag) => (
          <span key={tag} className="rounded-full bg-white/75 px-2.5 py-1 text-[10px] font-medium text-muted shadow-sm">
            {formatPredicate(tag)}
          </span>
        ))}
        {websiteUrl && (
          <a
            href={websiteUrl}
            target="_blank"
            rel="noreferrer"
            onClick={(event) => event.stopPropagation()}
            className="inline-flex items-center gap-1 rounded-full bg-accent-soft px-2.5 py-1 text-[10px] font-bold text-accent"
          >
            Website <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3 rounded-md bg-surface-2/70 px-3 py-2.5">
        {onOutreach && (
          <button
            onClick={(event) => {
              event.stopPropagation();
              onOutreach();
            }}
            className="inline-flex items-center gap-1.5 text-xs font-bold text-accent"
          >
            <Send className="h-3.5 w-3.5" /> Outreach
          </button>
        )}
        <button
          onClick={(event) => {
            event.stopPropagation();
            setFeedbackOpen(true);
          }}
          className="text-xs font-semibold text-muted hover:text-danger"
        >
          Dismiss
        </button>
        <button onClick={onViewFounder} className="ml-auto flex items-center gap-1 text-xs font-bold text-accent">
          {"View Founder"}<ArrowUpRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
        </button>
      </div>
      {feedbackOpen && (
        <div className="mt-3 rounded-md border border-line bg-white p-3" onClick={(event) => event.stopPropagation()}>
          <label htmlFor={`dismiss-reason-${candidate.id}`} className="text-xs font-semibold text-ink-2">
            Why dismiss this candidate?
          </label>
          <textarea
            id={`dismiss-reason-${candidate.id}`}
            value={dismissReason}
            onChange={(event) => setDismissReason(event.target.value)}
            className="mt-2 min-h-16 w-full rounded-md border border-line bg-surface-2 p-2 text-xs outline-none focus:border-accent-muted"
            placeholder="Record a review reason"
          />
          {feedbackState === "error" && <p className="mt-1 text-xs font-semibold text-danger">Unable to save feedback. Try again.</p>}
          <div className="mt-2 flex justify-end gap-2">
            <button type="button" onClick={() => setFeedbackOpen(false)} className="rounded-md px-3 py-1.5 text-xs font-semibold text-muted">Cancel</button>
            <button
              type="button"
              disabled={feedbackState === "saving" || dismissReason.trim().length < 3}
              onClick={async () => {
                setFeedbackState("saving");
                try {
                  await recordCandidateFeedback(candidate.id, "dismiss", dismissReason.trim());
                  setDismissed(true);
                } catch {
                  setFeedbackState("error");
                }
              }}
              className="rounded-md bg-accent px-3 py-1.5 text-xs font-bold text-white disabled:opacity-40"
            >
              {feedbackState === "saving" ? "Saving…" : "Save dismissal"}
            </button>
          </div>
        </div>
      )}
    </article>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: number | null | undefined;
}) {
  const visual = scoreVisual(value);
  const circumference = 2 * Math.PI * 26;
  const offset = circumference * (1 - (visual.percent ?? 0) / 100);

  return (
    <div className="flex min-w-0 flex-col items-center rounded-md bg-white/70 px-2 py-3 text-center shadow-[0_6px_18px_rgba(70,91,120,.06)]">
      <div
        role="progressbar"
        aria-label={`${label} score`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={visual.percent ?? undefined}
        aria-valuetext={visual.percent == null ? "No score" : `${visual.percent}% · ${visual.status}`}
        className="relative h-[72px] w-[72px]"
      >
        <svg viewBox="0 0 72 72" className="h-full w-full -rotate-90" aria-hidden="true">
          <circle cx="36" cy="36" r="26" fill="none" stroke="#e7edf4" strokeWidth="7" />
          <circle
            cx="36"
            cy="36"
            r="26"
            fill="none"
            stroke={visual.color}
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-[stroke-dashoffset] duration-500"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="numeric text-[15px] font-bold" style={{ color: visual.color }}>
            {visual.percent == null ? "—" : `${visual.percent}%`}
          </span>
        </div>
      </div>
      <div className="mt-2 flex min-w-0 items-center justify-center gap-1.5 text-[11px] font-bold text-ink-2">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded" style={{ backgroundColor: visual.soft, color: visual.color }}>
          <Icon className="h-3 w-3" />
        </span>
        <span className="truncate">{label}</span>
      </div>
      <span className="mt-1 text-[9px] font-bold uppercase tracking-wider" style={{ color: visual.color }}>{visual.status}</span>
    </div>
  );
}

function EvidenceBar({ value }: { value: number | null | undefined }) {
  const visual = scoreVisual(value);
  return (
    <div className="mt-3 rounded-md bg-white/60 px-3 py-2.5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 text-[10px] font-bold text-ink-2">
          <ShieldCheck className="h-3.5 w-3.5" style={{ color: visual.color }} /> Evidence confidence
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: visual.color }}>{visual.status}</span>
          <span className="numeric text-xs font-bold" style={{ color: visual.color }}>{percentage(value)}</span>
        </div>
      </div>
      <div
        role="progressbar"
        aria-label="Evidence confidence"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={visual.percent ?? undefined}
        aria-valuetext={visual.percent == null ? "No score" : `${visual.percent}% · ${visual.status}`}
        className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-3"
      >
        <div className="h-full rounded-full transition-[width] duration-500" style={{ width: `${visual.percent ?? 0}%`, backgroundColor: visual.color }} />
      </div>
    </div>
  );
}
