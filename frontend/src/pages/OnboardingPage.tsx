import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { ArrowRight, Banknote, Compass, Globe2, Layers3, Sparkles, Target } from "lucide-react";
import { saveActiveThesis, useActiveThesis } from "../api/theses";
import { ChoiceSection, SingleChoiceSection, SummaryRow } from "../components/onboarding/OnboardingChoices";
import { checkBand, checkRange, checks, labelsFor, regions, sectors, stages, toggleValue } from "../data/onboarding";

export function OnboardingPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: activeThesis } = useActiveThesis();
  const [selectedStages, setSelectedStages] = useState<string[]>(["pre-seed", "seed"]);
  const [selectedSectors, setSelectedSectors] = useState<string[]>(["ai", "deep-tech"]);
  const [selectedRegions, setSelectedRegions] = useState<string[]>(["dach", "europe"]);
  const [selectedCheck, setSelectedCheck] = useState("250-500");
  const [thesisName, setThesisName] = useState("Investment thesis");
  const [saveState, setSaveState] = useState<"idle" | "saving" | "error">("idle");

  useEffect(() => {
    if (!activeThesis) return;
    setThesisName(activeThesis.name);
    setSelectedStages(activeThesis.stages);
    setSelectedSectors(activeThesis.sectors);
    setSelectedRegions(activeThesis.regions);
    setSelectedCheck(checkBand(activeThesis.check_size_min_k_eur, activeThesis.check_size_max_k_eur));
  }, [activeThesis]);

  const summary = useMemo(() => ({ stages: labelsFor(stages, selectedStages), sectors: labelsFor(sectors, selectedSectors), regions: labelsFor(regions, selectedRegions), check: checks.find((item) => item.value === selectedCheck)?.label ?? "Not selected" }), [selectedStages, selectedSectors, selectedRegions, selectedCheck]);

  const saveAndScore = async () => {
    setSaveState("saving");
    const [minimum, maximum] = checkRange(selectedCheck);
    try {
      await saveActiveThesis({
        name: thesisName.trim() || "Investment thesis",
        stages: selectedStages,
        sectors: selectedSectors,
        excluded_sectors: activeThesis?.excluded_sectors ?? [],
        regions: selectedRegions,
        check_size_min_k_eur: minimum,
        check_size_max_k_eur: maximum,
        ownership_target_pct: activeThesis?.ownership_target_pct ?? 10,
        risk_appetite: activeThesis?.risk_appetite ?? "balanced",
        scoring_weights: activeThesis?.scoring_weights ?? { stage: 0.30, sector: 0.40, geography: 0.20, check_size: 0.10 },
        discovery_queries: activeThesis?.discovery_queries ?? [],
        source_freshness_days: activeThesis?.source_freshness_days ?? {},
      });
      await Promise.all([queryClient.invalidateQueries({ queryKey: ["active-thesis"] }), queryClient.invalidateQueries({ queryKey: ["candidates"] })]);
      navigate("/sourcing");
    } catch {
      setSaveState("error");
    }
  };

  return <div className="mx-auto max-w-[1180px] pb-10 pt-2"><div className="mb-8 max-w-2xl"><div className="eyebrow mb-2">Welcome to FirstCheck24</div><h1 className="page-title">What are you looking to invest in?</h1><p className="page-description">Choose a few basics. You can refine your thesis later as the system learns from your decisions.</p></div><div className="grid gap-6 lg:grid-cols-[1fr_320px]"><div className="space-y-4"><label className="panel block rounded-lg p-4"><span className="data-label mb-2 block">Thesis name</span><input value={thesisName} onChange={(event) => setThesisName(event.target.value)} maxLength={255} className="w-full rounded-md bg-surface-2 px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-accent/20" /></label><ChoiceSection icon={Layers3} title="Investment stage" hint="Choose one or more" options={stages} selected={selectedStages} onToggle={(value) => setSelectedStages(toggleValue(selectedStages, value))} /><ChoiceSection icon={Sparkles} title="Sectors" hint="Choose the themes you understand best" options={sectors} selected={selectedSectors} onToggle={(value) => setSelectedSectors(toggleValue(selectedSectors, value))} compact /><ChoiceSection icon={Globe2} title="Geography" hint="Where should we look for founders?" options={regions} selected={selectedRegions} onToggle={(value) => setSelectedRegions(toggleValue(selectedRegions, value))} compact /><SingleChoiceSection icon={Banknote} title="Typical first check" options={checks} selected={selectedCheck} onSelect={setSelectedCheck} /></div><aside className="h-fit lg:sticky lg:top-24"><div className="panel rounded-lg p-5"><div className="mb-5 flex items-center gap-3"><div className="flex h-9 w-9 items-center justify-center rounded-md bg-accent-soft text-accent"><Target className="h-4 w-4" /></div><div><h2 className="section-title">Your starting thesis</h2><p className="supporting-text">{activeThesis ? `${activeThesis.version} · active` : "New thesis"}</p></div></div><div className="space-y-4"><SummaryRow label="Stage" value={summary.stages} /><SummaryRow label="Sector" value={summary.sectors} /><SummaryRow label="Geography" value={summary.regions} /><SummaryRow label="First check" value={summary.check} /></div><div className="my-5 border-t border-line" /><div className="mb-5 flex gap-2 rounded-md bg-surface-2 p-3 text-xs leading-5 text-muted"><Compass className="mt-0.5 h-4 w-4 shrink-0 text-accent" />We’ll use these preferences to rank founders. Missing public history will never count against founder quality.</div><button onClick={() => void saveAndScore()} disabled={saveState === "saving" || !thesisName.trim() || !selectedStages.length || !selectedSectors.length || !selectedRegions.length} className="flex w-full items-center justify-center gap-2 rounded-md bg-accent px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#344c6c] disabled:cursor-not-allowed disabled:opacity-40">{saveState === "saving" ? "Saving & scoring…" : "Save thesis & score founders"} <ArrowRight className="h-4 w-4" /></button>{saveState === "error" && <p className="mt-3 text-center text-[11px] font-semibold text-danger">Unable to save the thesis. Please retry.</p>}<button onClick={() => navigate("/sourcing")} className="mt-3 w-full text-center text-xs font-semibold text-muted hover:text-accent">Skip for now</button></div></aside></div></div>;
}
