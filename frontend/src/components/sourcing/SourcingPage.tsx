import { useState } from "react";
import { Search, ChevronDown, TrendingUp, Zap } from "lucide-react";
import { useCandidates } from "../../api/candidates";
import { mockCandidates } from "../../data/mockCandidates";
import { CandidateCard } from "./CandidateCard";
import { Chip } from "./Chip";

type ChipType = "exact" | "semantic" | "graph" | "exclusion" | "uncertain";

interface QueryChip {
  id: string;
  label: string;
  type: ChipType;
}

const defaultChips: QueryChip[] = [
  { id: "c1", label: "Technical founder", type: "semantic" },
  { id: "c2", label: "Berlin", type: "exact" },
  { id: "c3", label: "AI infrastructure", type: "semantic" },
  { id: "c4", label: "Enterprise traction", type: "uncertain" },
  { id: "c5", label: "No prior VC backing", type: "exclusion" },
];

const chipStyles: Record<ChipType, { bg: string; text: string; border: string; label: string }> = {
  exact: { bg: "#1A2E2D", text: "#2DD4BF", border: "#115E59", label: "Exact filter" },
  semantic: { bg: "#1E1F3A", text: "#818CF8", border: "#3730A3", label: "Semantic concept" },
  graph: { bg: "#2A1F0E", text: "#FBBF24", border: "#92400E", label: "Graph constraint" },
  exclusion: { bg: "#2A1111", text: "#FCA5A5", border: "#991B1B", label: "Exclusion" },
  uncertain: { bg: "#1F2128", text: "#9CA3AF", border: "#4B5563", label: "Uncertain — review" },
};

export function SourcingPage() {
  const { data: apiCandidates, isLoading, error } = useCandidates();
  const [query, setQuery] = useState(
    "Technical founder in Berlin building AI infrastructure with enterprise traction and no prior VC backing.",
  );
  const [chips, setChips] = useState<QueryChip[]>(defaultChips);
  const [sortBy] = useState("Thesis Fit");

  // Use API data if available, fall back to mock data
  const candidates = apiCandidates && apiCandidates.length > 0 ? apiCandidates : mockCandidates;

  const removeChip = (id: string) => setChips(chips.filter((c) => c.id !== id));

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-ink">Sourcing Feed</h1>
        <p className="text-sm text-muted-2">
          Ranked candidates discovered across 9 signal sources · Updated 3 minutes ago
        </p>
      </div>

      {/* NL Search */}
      <div className="bg-surface border border-line rounded-lg p-4 mb-4">
        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-2" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 text-sm rounded-md border border-line outline-none focus:border-accent transition-colors bg-surface text-ink placeholder:text-muted-2"
          />
        </div>

        {/* Interpreted chips */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted-2">Interpreted as:</span>
          {chips.map((chip) => (
            <Chip key={chip.id} id={chip.id} label={chip.label} type={chip.type} onRemove={removeChip} />
          ))}
          <button className="text-xs text-accent hover:underline flex items-center gap-1">
            + Add criterion
          </button>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-4 mt-3 pt-3 border-t border-line">
          {Object.entries(chipStyles).map(([type, style]) => (
            <span key={type} className="flex items-center gap-1 text-xs text-muted-2">
              <span
                className="w-2 h-2 rounded-full border"
                style={{ background: style.bg, borderColor: style.border }}
              />
              {style.label}
            </span>
          ))}
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm text-muted-2">
          {candidates.length} candidates · Ranked by thesis fit
        </span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-2">Sort by:</span>
          <button className="flex items-center gap-1 text-sm border border-line rounded px-2 py-1 text-ink hover:border-line-2 bg-surface">
            {sortBy} <ChevronDown className="w-3.5 h-3.5 ml-1 text-muted-2" />
          </button>
          <button className="flex items-center gap-1 text-xs border border-line rounded px-2 py-1 text-muted hover:border-line-2 bg-surface">
            <TrendingUp className="w-3 h-3" />
            Filters
          </button>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="text-center py-8 text-sm text-muted-2">
          <Zap className="w-6 h-6 mx-auto mb-2 text-muted-2 animate-pulse" />
          Loading candidates...
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div className="text-center py-8 text-sm text-danger">
          <p>Failed to load candidates. Showing mock data.</p>
        </div>
      )}

      {/* Cards */}
      {!isLoading && (
        <div className="space-y-3">
          {candidates.map((candidate) => (
            <CandidateCard
              key={candidate.id}
              candidate={candidate}
              onViewFounder={() => console.log("View founder:", candidate.id)}
              onAddPipeline={() => console.log("Add to pipeline:", candidate.id)}
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && candidates.length === 0 && (
        <div className="text-center py-8 text-sm text-muted-2">
          <Search className="w-6 h-6 mx-auto mb-2 text-muted-2" />
          Refine your query to surface more candidates
        </div>
      )}
    </div>
  );
}
