import type { ElementType } from "react";

type MetricTone = "blue" | "green" | "purple" | "amber" | "rose";

const tones: Record<MetricTone, { color: string; soft: string; glow: string }> = {
  blue: { color: "#557dc0", soft: "#e7eef9", glow: "rgba(85,125,192,.16)" },
  green: { color: "#2f8b72", soft: "#e4f2ed", glow: "rgba(47,139,114,.15)" },
  purple: { color: "#7656a5", soft: "#eee8f8", glow: "rgba(118,86,165,.14)" },
  amber: { color: "#b87932", soft: "#fff1df", glow: "rgba(198,137,63,.16)" },
  rose: { color: "#b9575f", soft: "#fbe8e9", glow: "rgba(195,95,101,.15)" },
};

export function KeyMetricCard({
  icon: Icon,
  label,
  value,
  suffix,
  detail,
  progress,
  progressLabel,
  tone,
}: {
  icon: ElementType;
  label: string;
  value: number | null;
  suffix?: string;
  detail: string;
  progress: number | null;
  progressLabel: string;
  tone: MetricTone;
}) {
  const visual = tones[tone];
  const normalizedProgress = progress == null ? 0 : Math.max(0, Math.min(100, Math.round(progress)));

  return (
    <article className="panel group relative isolate overflow-hidden rounded-lg px-4 py-3.5">
      <div
        className="pointer-events-none absolute -right-8 -top-12 -z-10 h-24 w-24 rounded-full blur-3xl transition-transform duration-300 group-hover:scale-125"
        style={{ backgroundColor: visual.glow }}
      />
      <div className="flex min-w-0 items-center gap-3">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md" style={{ color: visual.color, backgroundColor: visual.soft }}>
          <Icon className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="data-label">{label}</div>
          <p className="mt-1 text-[10px] font-medium leading-4 text-muted" title={detail}>{detail}</p>
        </div>
        <div className="flex shrink-0 items-end gap-0.5">
          <span className="numeric text-[1.55rem] font-bold leading-none tracking-[-.04em] text-ink">{value == null ? "Not scored" : value}</span>
          {suffix && value != null && <span className="mb-px text-[11px] font-bold" style={{ color: visual.color }}>{suffix}</span>}
        </div>
      </div>

      <div className="mt-2.5 flex items-center gap-2.5">
        <div
          className="h-1.5 min-w-12 flex-1 overflow-hidden rounded-full"
          role="progressbar"
          aria-label={`${label}: ${progress == null ? "pending" : progressLabel}`}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress == null ? undefined : normalizedProgress}
          style={{ backgroundColor: visual.soft }}
        >
          <div className="h-full rounded-full transition-[width] duration-500" style={{ width: `${normalizedProgress}%`, backgroundColor: visual.color }} />
        </div>
        <div className="flex max-w-[48%] shrink-0 items-center gap-1.5">
          <span className="truncate text-[9px] font-semibold text-muted">{progressLabel}</span>
          <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: visual.color }} />
        </div>
      </div>
    </article>
  );
}
