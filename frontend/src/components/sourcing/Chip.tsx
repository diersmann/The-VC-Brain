import { X } from "lucide-react";

type ChipType = "exact" | "semantic" | "graph" | "exclusion" | "uncertain";

interface ChipProps {
  label: string;
  type: ChipType;
  onRemove: (id: string) => void;
  id: string;
}

const chipStyles: Record<ChipType, { bg: string; text: string; border: string; label: string }> = {
  exact: { bg: "#EAF8F4", text: "#287568", border: "#C7EADF", label: "Exact filter" },
  semantic: { bg: "#EEF1FF", text: "#5C67A8", border: "#D9DEFA", label: "Semantic concept" },
  graph: { bg: "#FFF6DF", text: "#916C22", border: "#F4E3B5", label: "Graph constraint" },
  exclusion: { bg: "#FFF0F0", text: "#A15757", border: "#F5D7D7", label: "Exclusion" },
  uncertain: { bg: "#F2F4F7", text: "#667085", border: "#E2E7ED", label: "Uncertain — review" },
};

export function Chip({ label, type, onRemove, id }: ChipProps) {
  const style = chipStyles[type];
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium shadow-[0_1px_2px_rgba(24,39,75,0.04)]"
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
