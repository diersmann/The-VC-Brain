import { X } from "lucide-react";

type ChipType = "exact" | "semantic" | "graph" | "exclusion" | "uncertain";

interface ChipProps {
  label: string;
  type: ChipType;
  onRemove: (id: string) => void;
  id: string;
}

const chipStyles: Record<ChipType, { bg: string; text: string; border: string; label: string }> = {
  exact: { bg: "#1A2E2D", text: "#2DD4BF", border: "#115E59", label: "Exact filter" },
  semantic: { bg: "#1E1F3A", text: "#818CF8", border: "#3730A3", label: "Semantic concept" },
  graph: { bg: "#2A1F0E", text: "#FBBF24", border: "#92400E", label: "Graph constraint" },
  exclusion: { bg: "#2A1111", text: "#FCA5A5", border: "#991B1B", label: "Exclusion" },
  uncertain: { bg: "#1F2128", text: "#9CA3AF", border: "#4B5563", label: "Uncertain — review" },
};

export function Chip({ label, type, onRemove, id }: ChipProps) {
  const style = chipStyles[type];
  return (
    <span
      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs border"
      style={{ background: style.bg, color: style.text, borderColor: style.border }}
      title={style.label}
    >
      {label}
      <button
        onClick={() => onRemove(id)}
        className="ml-0.5 hover:opacity-70 transition-opacity"
      >
        <X className="w-3 h-3" />
      </button>
    </span>
  );
}
