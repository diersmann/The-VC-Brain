import { useState } from "react";
import {
  Eye,
  Info,
  Plus,
  MessageSquare,
  XCircle,
  CheckCircle,
} from "lucide-react";
import type { Candidate } from "../../types/candidate";
import { ScoreBar } from "./ScoreBar";

interface CandidateCardProps {
  candidate: Candidate;
  onViewFounder: () => void;
  onAddPipeline: () => void;
}

function getInitials(name: string | null): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

export function CandidateCard({ candidate, onViewFounder, onAddPipeline }: CandidateCardProps) {
  const [dismissed, setDismissed] = useState(false);
  const [showEvidence, setShowEvidence] = useState(false);
  if (dismissed) return null;

  const isInbound = candidate.origin === "inbound";
  const initials = getInitials(candidate.display_name);
  const hasScores = candidate.scores !== null;

  return (
    <div className="bg-surface border border-line rounded-lg p-5 hover:border-line-2 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full flex items-center justify-center text-white text-sm flex-shrink-0 bg-accent">
            {initials}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-ink font-medium">
                {candidate.display_name ?? candidate.stable_id}
              </span>
              <span
                className={`text-xs px-1.5 py-0.5 rounded ${
                  isInbound
                    ? "bg-[#1E1F3A] text-[#818CF8]"
                    : "bg-[#1A2E2D] text-[#2DD4BF]"
                }`}
              >
                {isInbound ? "Inbound" : "Outbound"}
              </span>
            </div>
            <div className="text-sm text-muted">
              {candidate.email ?? "—"} · {candidate.consent_state}
            </div>
            <div className="text-xs text-muted-2">
              {candidate.handles?.linkedin ?? "—"} · via {candidate.origin ?? "unknown"}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-xs text-muted-2">
            {candidate.latest_score_at
              ? new Date(candidate.latest_score_at).toLocaleDateString()
              : "No scores yet"}
          </span>
        </div>
      </div>

      {/* Scores */}
      <div className="grid grid-cols-4 gap-3 mb-3">
        <ScoreBar
          label="Novelty"
          value={hasScores ? candidate.scores!.novelty : null}
          color="#2DD4BF"
        />
        <ScoreBar
          label="Momentum"
          value={hasScores ? candidate.scores!.momentum : null}
          color="#818CF8"
        />
        <ScoreBar
          label="Thesis Fit"
          value={hasScores ? candidate.scores!.thesis_fit : null}
          color="#F97316"
        />
        <ScoreBar
          label="Evidence"
          value={hasScores ? candidate.scores!.evidence_confidence : null}
          color="#9CA3AF"
        />
      </div>

      {/* Identity match */}
      <div className="flex items-center gap-1 mb-3 text-xs text-muted-2">
        <CheckCircle className="w-3 h-3 text-accent" />
        Identity match:{" "}
        <span className="tabular-nums">
          {hasScores ? `${Math.round((candidate.scores!.evidence_confidence ?? 0) * 100)}%` : "—"}
        </span>
        <span className="mx-1 text-line-2">·</span>
        <Info className="w-3 h-3 text-muted-2" />
        {candidate.consent_state === "granted" ? "Consented" : "Pending consent"}
      </div>

      {/* Why surfaced */}
      {showEvidence && (
        <div className="rounded-md p-3 mb-3 text-xs space-y-1.5 bg-surface-2 border-l-[3px] border-accent">
          <div className="text-muted-2 mb-1">Why surfaced:</div>
          <div className="flex items-start gap-1.5 text-muted">
            <div className="w-1 h-1 rounded-full bg-muted-2 mt-1.5 flex-shrink-0" />
            Discovered via {candidate.origin ?? "unknown"} channel
          </div>
          <div className="flex items-start gap-1.5 text-muted">
            <div className="w-1 h-1 rounded-full bg-muted-2 mt-1.5 flex-shrink-0" />
            {hasScores
              ? `Thesis fit score: ${candidate.scores!.thesis_fit}`
              : "No scoring data available"}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-2 border-t border-line">
        <button
          onClick={onViewFounder}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-white bg-accent hover:opacity-90 transition-opacity"
        >
          <Eye className="w-3.5 h-3.5" />
          View Founder
        </button>
        <button
          onClick={() => setShowEvidence(!showEvidence)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm border border-line text-muted hover:border-line-2 transition-colors"
        >
          <Info className="w-3.5 h-3.5" />
          {showEvidence ? "Hide" : "View Evidence"}
        </button>
        <button
          onClick={onAddPipeline}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm border border-line text-muted hover:border-line-2 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          Add to Pipeline
        </button>
        <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm border border-line text-muted hover:border-line-2 transition-colors">
          <MessageSquare className="w-3.5 h-3.5" />
          Draft Outreach
        </button>
        <button
          onClick={() => setDismissed(true)}
          className="ml-auto flex items-center gap-1 px-3 py-1.5 rounded-md text-xs text-muted-2 hover:text-danger transition-colors"
        >
          <XCircle className="w-3.5 h-3.5" />
          Dismiss
        </button>
      </div>
    </div>
  );
}
