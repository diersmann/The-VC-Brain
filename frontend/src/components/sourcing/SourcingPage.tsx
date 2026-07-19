import { useState } from "react";
import { useNavigate } from "react-router";
import { Search, ChevronDown, Sparkles, Users, Radar, TrendingUp, Plus } from "lucide-react";
import { triggerDiscovery, useCandidates } from "../../api/candidates";
import type { Candidate } from "../../types/candidate";
import { CandidateCard } from "./CandidateCard";
import { Chip } from "./Chip";

type ChipType = "exact" | "semantic" | "graph" | "exclusion" | "uncertain";
const defaultChips: {id:string;label:string;type:ChipType}[] = [
  {id:"c1",label:"Technical founder",type:"semantic"},{id:"c2",label:"Berlin",type:"exact"},{id:"c3",label:"AI infrastructure",type:"semantic"},{id:"c4",label:"Enterprise traction",type:"uncertain"},{id:"c5",label:"No prior VC backing",type:"exclusion"},
];

export function SourcingPage() {
  const navigate=useNavigate(); const {data,isLoading,error,refetch}=useCandidates();
  const records=data??[];
  const candidates=records.filter(hasPublicName).sort((left,right)=>axisScore(right)-axisScore(left));
  const unresolvedLeads=records.length-candidates.length;
  const [query,setQuery]=useState("Berlin");
  const [chips,setChips]=useState(defaultChips);
  const [discovering,setDiscovering]=useState(false);
  const runDiscovery=async()=>{setDiscovering(true);try{await triggerDiscovery(query,"github");window.setTimeout(()=>void refetch(),5000);}finally{setDiscovering(false)}};
  const highSignal=candidates.filter(candidate=>axisScore(candidate)>=.67).length;
  const recentlyAdded=candidates.filter(candidate=>candidate.created_at&&Date.now()-new Date(candidate.created_at).getTime()<7*86400000).length;
  return <div>
    <section className="mb-6 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
      <div><div className="eyebrow mb-2">Intelligence workspace</div><h1 className="text-3xl font-bold tracking-tight text-ink">Founder discovery</h1><p className="mt-1.5 max-w-2xl text-sm text-muted">Evidence-backed signals from products, research, communities and founder-submitted material.</p></div>
      <button className="flex w-fit items-center gap-2 rounded-md bg-accent px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-slate-300"><Plus className="h-4 w-4"/>Add candidate</button>
    </section>

    <div className="mb-6 grid gap-3 sm:grid-cols-3">
      {[
        {icon:Users,label:"Verified candidates",value:String(candidates.length),hint:"Real identity + evidence",tone:"bg-[#e8eef8] text-[#4e6f9e]",dot:"bg-[#6f8db7]"},
        {icon:Radar,label:"High multi-axis signal",value:String(highSignal),hint:"3-axis average ≥ 67%",tone:"bg-[#e7f3ef] text-[#38836e]",dot:"bg-[#4f9b84]"},
        {icon:TrendingUp,label:"Added this week",value:String(recentlyAdded),hint:"Public-source discovery",tone:"bg-[#f0eafa] text-[#7656a5]",dot:"bg-[#8b6db6]"},
      ].map(({icon:Icon,label,value,hint,tone,dot})=><div key={label} className="panel flex items-center gap-4 rounded-lg border-t-2 border-t-transparent p-4 transition hover:border-t-current"><div className={`flex h-11 w-11 items-center justify-center rounded-lg ${tone}`}><Icon className="h-5 w-5"/></div><div><div className="flex items-center gap-2 text-xl font-bold">{value}<span className={`h-1.5 w-1.5 rounded-full ${dot}`}/></div><div className="text-xs font-medium text-ink-2">{label}</div></div><span className="ml-auto self-end text-[10px] text-muted">{hint}</span></div>)}
    </div>

    <section className="panel mb-6 rounded-lg p-5">
      <div className="mb-3 flex items-center gap-2"><Sparkles className="h-4 w-4 text-accent"/><span className="text-xs font-semibold text-accent">Live GitHub founder discovery · search by location</span></div>
      <div className="flex gap-2"><div className="relative flex-1"><Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-2"/><input value={query} onChange={e=>setQuery(e.target.value)} className="w-full rounded-md border border-line bg-surface-2 py-3.5 pl-11 pr-4 text-sm outline-none focus:border-accent-muted"/></div><button onClick={runDiscovery} disabled={discovering||!query.trim()} className="rounded-md bg-accent px-4 text-xs font-bold text-white disabled:opacity-50">{discovering?"Queuing…":"Discover live"}</button></div>
      <div className="mt-4 flex flex-wrap items-center gap-2"><span className="text-[11px] font-medium text-muted">Interpreted as</span>{chips.map(c=><Chip key={c.id} {...c} onRemove={id=>setChips(v=>v.filter(x=>x.id!==id))}/>)}<button className="text-xs font-semibold text-accent">+ Add criterion</button></div>
    </section>

    <div className="mb-4 flex items-center justify-between"><div><h2 className="text-lg font-bold">Ranked candidates</h2><p className="text-xs text-muted">{candidates.length} verified profiles · {unresolvedLeads} handle-only leads excluded pending identity verification</p></div><button className="flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-semibold text-ink-2">Multi-axis score <ChevronDown className="h-3.5 w-3.5"/></button></div>
    {isLoading && <div className="py-16 text-center text-sm text-muted">Building evidence-backed ranking…</div>}
    {error && !isLoading && <div className="mb-3 rounded-md bg-[#fff8ed] px-4 py-2.5 text-xs text-[#9a6a2d]">The live candidate API is unavailable. No fallback data is being shown.</div>}
    {!isLoading&&!error&&candidates.length===0&&<div className="panel py-16 text-center"><div className="text-sm font-bold">No candidates with a public real name yet</div><p className="mt-2 text-xs text-muted">Run GitHub discovery above. Profiles without a published name are intentionally hidden.</p></div>}
    {!isLoading && <div className="grid gap-4 xl:grid-cols-2">{candidates.map(c=><CandidateCard key={c.id} candidate={c} onViewFounder={()=>navigate(`/founders/${c.id}`)} onAddPipeline={()=>{}} />)}</div>}
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
