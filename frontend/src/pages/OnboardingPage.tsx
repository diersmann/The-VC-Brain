import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import {
  ArrowRight,
  Banknote,
  Check,
  Compass,
  Globe2,
  Layers3,
  Sparkles,
  Target,
} from "lucide-react";

interface Option {
  label: string;
  value: string;
  description?: string;
}

const stages: Option[] = [
  { label: "Pre-seed", value: "pre-seed", description: "Idea to first signals" },
  { label: "Seed", value: "seed", description: "Early product-market proof" },
  { label: "Series A", value: "series-a", description: "Repeatable growth" },
];

const sectors: Option[] = [
  { label: "AI & Infrastructure", value: "ai" },
  { label: "Climate Tech", value: "climate" },
  { label: "Deep Tech", value: "deep-tech" },
  { label: "B2B Software", value: "b2b" },
  { label: "Fintech", value: "fintech" },
  { label: "Health & Biotech", value: "health" },
];

const regions: Option[] = [
  { label: "DACH", value: "dach" },
  { label: "Europe", value: "europe" },
  { label: "United Kingdom", value: "uk" },
  { label: "United States", value: "us" },
  { label: "Global", value: "global" },
];

const checks: Option[] = [
  { label: "€100k – €250k", value: "100-250" },
  { label: "€250k – €500k", value: "250-500" },
  { label: "€500k – €1m", value: "500-1000" },
  { label: "€1m+", value: "1000+" },
];

export function OnboardingPage() {
  const navigate = useNavigate();
  const [selectedStages, setSelectedStages] = useState<string[]>(["pre-seed", "seed"]);
  const [selectedSectors, setSelectedSectors] = useState<string[]>(["ai", "deep-tech"]);
  const [selectedRegions, setSelectedRegions] = useState<string[]>(["dach", "europe"]);
  const [selectedCheck, setSelectedCheck] = useState("250-500");

  const summary = useMemo(
    () => ({
      stages: labelsFor(stages, selectedStages),
      sectors: labelsFor(sectors, selectedSectors),
      regions: labelsFor(regions, selectedRegions),
      check: checks.find((item) => item.value === selectedCheck)?.label ?? "Not selected",
    }),
    [selectedStages, selectedSectors, selectedRegions, selectedCheck],
  );

  return (
    <div className="mx-auto max-w-[1180px] pb-10 pt-2">
      <div className="mb-8 max-w-2xl">
        <div className="eyebrow mb-2">Welcome to The VC Brain</div>
        <h1 className="text-3xl font-bold tracking-tight text-ink">What are you looking to invest in?</h1>
        <p className="mt-2 text-sm leading-6 text-muted">
          Choose a few basics. You can refine your thesis later as the system learns from your decisions.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          <ChoiceSection
            icon={Layers3}
            title="Investment stage"
            hint="Choose one or more"
            options={stages}
            selected={selectedStages}
            onToggle={(value) => setSelectedStages(toggleValue(selectedStages, value))}
          />
          <ChoiceSection
            icon={Sparkles}
            title="Sectors"
            hint="Choose the themes you understand best"
            options={sectors}
            selected={selectedSectors}
            onToggle={(value) => setSelectedSectors(toggleValue(selectedSectors, value))}
            compact
          />
          <ChoiceSection
            icon={Globe2}
            title="Geography"
            hint="Where should we look for founders?"
            options={regions}
            selected={selectedRegions}
            onToggle={(value) => setSelectedRegions(toggleValue(selectedRegions, value))}
            compact
          />
          <SingleChoiceSection
            icon={Banknote}
            title="Typical first check"
            options={checks}
            selected={selectedCheck}
            onSelect={setSelectedCheck}
          />
        </div>

        <aside className="h-fit lg:sticky lg:top-24">
          <div className="panel rounded-lg p-5">
            <div className="mb-5 flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-md bg-accent-soft text-accent">
                <Target className="h-4 w-4" />
              </div>
              <div>
                <h2 className="text-sm font-bold">Your starting thesis</h2>
                <p className="text-[11px] text-muted">You can change this anytime</p>
              </div>
            </div>

            <div className="space-y-4">
              <SummaryRow label="Stage" value={summary.stages} />
              <SummaryRow label="Sector" value={summary.sectors} />
              <SummaryRow label="Geography" value={summary.regions} />
              <SummaryRow label="First check" value={summary.check} />
            </div>

            <div className="my-5 border-t border-line" />
            <div className="mb-5 flex gap-2 rounded-md bg-surface-2 p-3 text-[11px] leading-5 text-muted">
              <Compass className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
              We’ll use these preferences to rank founders. Missing public history will never count against founder quality.
            </div>

            <button
              onClick={() => navigate("/sourcing")}
              disabled={!selectedStages.length || !selectedSectors.length || !selectedRegions.length}
              className="flex w-full items-center justify-center gap-2 rounded-md bg-accent px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#344c6c] disabled:cursor-not-allowed disabled:opacity-40"
            >
              Start discovering founders <ArrowRight className="h-4 w-4" />
            </button>
            <button onClick={() => navigate("/sourcing")} className="mt-3 w-full text-center text-xs font-semibold text-muted hover:text-accent">
              Skip for now
            </button>
          </div>
        </aside>
      </div>
    </div>
  );
}

function ChoiceSection({
  icon: Icon,
  title,
  hint,
  options,
  selected,
  onToggle,
  compact = false,
}: {
  icon: React.ElementType;
  title: string;
  hint: string;
  options: Option[];
  selected: string[];
  onToggle: (value: string) => void;
  compact?: boolean;
}) {
  return (
    <section className="panel rounded-lg p-5">
      <SectionTitle icon={Icon} title={title} hint={hint} />
      <div className={`grid gap-2.5 ${compact ? "sm:grid-cols-2 xl:grid-cols-3" : "sm:grid-cols-3"}`}>
        {options.map((option) => {
          const active = selected.includes(option.value);
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={active}
              onClick={() => onToggle(option.value)}
              className={`relative min-h-12 rounded-md border px-4 py-3 text-left transition ${
                active
                  ? "border-accent bg-accent-soft text-accent"
                  : "border-line bg-white text-ink-2 hover:border-line-2 hover:bg-surface-2"
              }`}
            >
              <div className="pr-6 text-xs font-bold">{option.label}</div>
              {option.description && <div className="mt-1 text-[10px] text-muted">{option.description}</div>}
              {active && <Check className="absolute right-3 top-3.5 h-3.5 w-3.5" />}
            </button>
          );
        })}
      </div>
    </section>
  );
}

function SingleChoiceSection({
  icon: Icon,
  title,
  options,
  selected,
  onSelect,
}: {
  icon: React.ElementType;
  title: string;
  options: Option[];
  selected: string;
  onSelect: (value: string) => void;
}) {
  return (
    <section className="panel rounded-lg p-5">
      <SectionTitle icon={Icon} title={title} hint="Choose one range" />
      <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-4">
        {options.map((option) => {
          const active = selected === option.value;
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={active}
              onClick={() => onSelect(option.value)}
              className={`flex items-center justify-between rounded-md border px-3 py-3 text-xs font-bold transition ${
                active ? "border-accent bg-accent text-white" : "border-line bg-white text-ink-2 hover:bg-surface-2"
              }`}
            >
              {option.label} {active && <Check className="h-3.5 w-3.5" />}
            </button>
          );
        })}
      </div>
    </section>
  );
}

function SectionTitle({ icon: Icon, title, hint }: { icon: React.ElementType; title: string; hint: string }) {
  const tone = title === "Investment stage"
    ? "bg-[#e7eef9] text-[#5074a8]"
    : title === "Sectors"
      ? "bg-[#eee8f8] text-[#7656a5]"
      : title === "Geography"
        ? "bg-[#e4f2ed] text-[#347c67]"
        : "bg-[#fff1df] text-[#a96e2d]";
  return (
    <div className="mb-4 flex items-center gap-3">
      <div className={`flex h-9 w-9 items-center justify-center rounded-md ${tone}`}>
        <Icon className="h-4 w-4" />
      </div>
      <div>
        <h2 className="text-sm font-bold">{title}</h2>
        <p className="text-[11px] text-muted">{hint}</p>
      </div>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] font-bold uppercase tracking-wider text-muted-2">{label}</div>
      <div className="mt-1 text-xs font-semibold leading-5 text-ink-2">{value || "Not selected"}</div>
    </div>
  );
}

function toggleValue(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

function labelsFor(options: Option[], values: string[]): string {
  return options.filter((option) => values.includes(option.value)).map((option) => option.label).join(", ");
}
