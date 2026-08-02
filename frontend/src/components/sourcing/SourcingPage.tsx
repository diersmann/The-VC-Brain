import { useState } from "react";
import { useNavigate } from "react-router";
import { Radar, Search, ShieldCheck, Sparkles, Target } from "lucide-react";
import { triggerDiscovery, useCandidates } from "../../api/candidates";
import { KeyMetricCard } from "../common/KeyMetricCard";
import { isEvidenceReady, isThesisAligned, ratioPercent } from "../../data/portfolioMetrics";
import { hasHighMultiAxisSignal } from "../../data/sourcingSignals";
import { DECISION_RUBRIC } from "../../data/rubric";
import type { Candidate } from "../../types/candidate";
import { CandidateCard } from "./CandidateCard";
import { OutreachComposer } from "./OutreachComposer";



export function SourcingPage() {
  const navigate=useNavigate(); const {data,isLoading,error,refetch}=useCandidates();
  const records=data??[];
  const candidates=records.filter(hasPublicName).sort((left,right)=>axisScore(right)-axisScore(left));
  const unresolvedLeads=records.length-candidates.length;
  const [query,setQuery]=useState("technical founder, Berlin, AI infra, enterprise traction, no prior VC backing, top-tier accelerator.");
  const [discovering,setDiscovering]=useState(false);
  const [discoveryError,setDiscoveryError]=useState(false);
  const [outreachCandidate,setOutreachCandidate]=useState<Candidate|null>(null);
  const runDiscovery=async()=>{setDiscovering(true);setDiscoveryError(false);try{await triggerDiscovery(query,"github");window.setTimeout(()=>void refetch(),5000);}catch{setDiscoveryError(true)}finally{setDiscovering(false)}};
  const highSignal=candidates.filter(hasHighMultiAxisSignal).length;
  const thesisAligned=candidates.filter(isThesisAligned).length;
  const evidenceReady=candidates.filter(isEvidenceReady).length;
  return <div>
    <section className="mb-6">
      <div><div className="eyebrow mb-2">Intelligence workspace</div><h1 className="page-title">Founder discovery</h1><p className="page-description">Evidence-backed signals from products, research, communities and founder-submitted material.</p></div>
    </section>

    <div className="mb-6 grid gap-3 sm:grid-cols-3">
      <KeyMetricCard icon={Radar} label="High multi-axis" value={highSignal} detail="Founder, Market and Idea × Market all score ≥67%" progress={ratioPercent(highSignal, candidates.length)} progressLabel={`${highSignal} of ${candidates.length} verified profiles`} tone="green" />
      <KeyMetricCard icon={Target} label="Thesis aligned" value={thesisAligned} detail="Candidates clearing the active thesis threshold" progress={ratioPercent(thesisAligned, candidates.length)} progressLabel={`${thesisAligned} of ${candidates.length} verified profiles`} tone="purple" />
      <KeyMetricCard icon={ShieldCheck} label="Evidence ready" value={evidenceReady} detail={`Profiles with at least ${DECISION_RUBRIC.evidenceConfidence}% evidence confidence`} progress={ratioPercent(evidenceReady, candidates.length)} progressLabel={`${evidenceReady} of ${candidates.length} verified profiles`} tone="blue" />
    </div>

    <section className="panel mb-6 rounded-lg p-5">
      <div className="mb-3 flex items-center gap-2"><Sparkles className="h-4 w-4 text-accent"/><span className="text-xs font-semibold text-accent">Live GitHub founder discovery · search by location</span></div>
      <div className="flex gap-2"><div className="relative flex-1"><Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-2"/><label htmlFor="discovery-query" className="sr-only">Discovery query</label><input id="discovery-query" value={query} onChange={e=>setQuery(e.target.value)} className="w-full rounded-md border border-line bg-surface-2 py-3.5 pl-11 pr-4 text-sm outline-none focus:border-accent-muted"/></div><button onClick={() => void runDiscovery()} disabled={discovering||!query.trim()} className="rounded-md bg-accent px-4 text-xs font-bold text-white disabled:opacity-50">{discovering?"Queuing…":"Discover live"}</button></div>
      {discoveryError && <div role="alert" className="mt-3 rounded-md border border-danger/20 bg-[#fbe8e9] px-3 py-2 text-xs font-semibold text-danger">Unable to queue discovery. Check the API service and retry.</div>}
    </section>

    <div className="mb-4"><h2 className="section-title">Ranked candidates</h2><p className="supporting-text"><span className="numeric">{candidates.length}</span> verified profiles · <span className="numeric">{unresolvedLeads}</span> handle-only leads excluded pending identity verification</p></div>
    {isLoading && <div className="py-16 text-center text-sm text-muted">Building evidence-backed ranking…</div>}
    {error && !isLoading && <div className="mb-3 rounded-md bg-[#fff8ed] px-4 py-2.5 text-xs text-[#9a6a2d]">The live candidate API is unavailable. No fallback data is being shown.</div>}
    {!isLoading&&!error&&candidates.length===0&&<div className="panel py-16 text-center"><div className="text-sm font-bold">No candidates with a public real name yet</div><p className="mt-2 text-xs text-muted">Run GitHub discovery above. Profiles without a published name are intentionally hidden.</p></div>}
    {!isLoading && <div className="grid gap-4 xl:grid-cols-2">{candidates.map(c=><CandidateCard key={c.id} candidate={c} onViewFounder={()=>navigate(`/founders/${c.id}`)} onOutreach={()=>setOutreachCandidate(c)} />)}</div>}
    {outreachCandidate && <OutreachComposer key={outreachCandidate.id} candidate={outreachCandidate} onClose={()=>setOutreachCandidate(null)} />}
  </div>;
}

function hasPublicName(candidate: Candidate): boolean {
  if (!candidate.display_name) return false;
  const handles = Object.values(candidate.handles ?? {}).map((value) => value.toLowerCase());
  return !handles.includes(candidate.display_name.toLowerCase());
}

function axisScore(candidate: Candidate): number {
  const values = [
    candidate.scores?.founder ?? candidate.scores?.raw?.founder,
    candidate.scores?.market ?? candidate.scores?.raw?.market,
    candidate.scores?.idea_market ?? candidate.scores?.raw?.idea_market,
  ].filter((value): value is number => typeof value === "number");
  if (values.length) return values.reduce((sum,value)=>sum+value,0)/values.length;
  return candidate.scores?.discovery_signal ?? candidate.scores?.raw?.composite ?? 0;
}
