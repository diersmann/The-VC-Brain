import { Check } from "lucide-react";
import type { Option } from "../../data/onboarding";

export function ChoiceSection({ icon: Icon, title, hint, options, selected, onToggle, compact = false }: { icon: React.ElementType; title: string; hint: string; options: Option[]; selected: string[]; onToggle: (value: string) => void; compact?: boolean }) {
  return <section className="panel rounded-lg p-5"><SectionTitle icon={Icon} title={title} hint={hint} /><div className={`grid gap-2.5 ${compact ? "sm:grid-cols-2 xl:grid-cols-3" : "sm:grid-cols-3"}`}>{options.map((option) => { const active = selected.includes(option.value); return <button key={option.value} type="button" aria-pressed={active} onClick={() => onToggle(option.value)} className={`relative min-h-12 rounded-md border px-4 py-3 text-left transition ${active ? "border-accent bg-accent-soft text-accent" : "border-line bg-white text-ink-2 hover:border-line-2 hover:bg-surface-2"}`}><div className="pr-6 text-[13px] font-bold">{option.label}</div>{option.description && <div className="mt-1 text-[11px] leading-4 text-muted">{option.description}</div>}{active && <Check className="absolute right-3 top-3.5 h-3.5 w-3.5" />}</button>; })}</div></section>;
}

export function SingleChoiceSection({ icon: Icon, title, options, selected, onSelect }: { icon: React.ElementType; title: string; options: Option[]; selected: string; onSelect: (value: string) => void }) {
  return <section className="panel rounded-lg p-5"><SectionTitle icon={Icon} title={title} hint="Choose one range" /><div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-4">{options.map((option) => { const active = selected === option.value; return <button key={option.value} type="button" aria-pressed={active} onClick={() => onSelect(option.value)} className={`flex items-center justify-between rounded-md border px-3 py-3 text-xs font-bold transition ${active ? "border-accent bg-accent text-white" : "border-line bg-white text-ink-2 hover:bg-surface-2"}`}>{option.label} {active && <Check className="h-3.5 w-3.5" />}</button>; })}</div></section>;
}

export function SectionTitle({ icon: Icon, title, hint }: { icon: React.ElementType; title: string; hint: string }) {
  const tone = title === "Investment stage" ? "bg-[#e7eef9] text-[#5074a8]" : title === "Sectors" ? "bg-[#eee8f8] text-[#7656a5]" : title === "Geography" ? "bg-[#e4f2ed] text-[#347c67]" : "bg-[#fff1df] text-[#a96e2d]";
  return <div className="mb-4 flex items-center gap-3"><div className={`flex h-9 w-9 items-center justify-center rounded-md ${tone}`}><Icon className="h-4 w-4" /></div><div><h2 className="section-title">{title}</h2><p className="supporting-text">{hint}</p></div></div>;
}

export function SummaryRow({ label, value }: { label: string; value: string }) {
  return <div><div className="data-label">{label}</div><div className="data-value leading-5">{value || "Not selected"}</div></div>;
}
