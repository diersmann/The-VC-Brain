interface ScoreBarProps {
  value: number | null;
  max?: number;
  color: string;
  label: string;
}

export function ScoreBar({ value, max = 100, color, label }: ScoreBarProps) {
  const hasValue = value !== null && value !== undefined;
  const pct = hasValue ? Math.min((value / max) * 100, 100) : 0;

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-2">{label}</span>
        <span className="text-xs tabular-nums text-muted w-7 text-right">
          {hasValue ? value : "—"}
        </span>
      </div>
      <div className="h-1 bg-surface-3 rounded-full overflow-hidden">
        {hasValue ? (
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${pct}%`, background: color }}
          />
        ) : (
          <div className="h-full w-full rounded-full bg-surface-3" />
        )}
      </div>
    </div>
  );
}
