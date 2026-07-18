import { useState } from "react";
import { useNavigate } from "react-router";
import { Search, ChevronDown, Sparkles, Users, Radar, TrendingUp, Plus } from "lucide-react";
import { useCandidates } from "../../api/candidates";
import { mockCandidates } from "../../data/mockCandidates";
import { CandidateCard } from "./CandidateCard";
import { Chip } from "./Chip";

type ChipType = "exact" | "semantic" | "graph" | "exclusion" | "uncertain";
const defaultChips: {id:string;label:string;type:ChipType}[] = [
  {id:"c1",label:"Technical founder",type:"semantic"},{id:"c2",label:"Berlin",type:"exact"},{id:"c3",label:"AI infrastructure",type:"semantic"},{id:"c4",label:"Enterprise traction",type:"uncertain"},{id:"c5",label:"No prior VC backing",type:"exclusion"},
];

export function SourcingPage() {
  const navigate=useNavigate(); const {data,isLoading,error}=useCandidates();
  const candidates=data?.length ? data : mockCandidates;
  const [query,setQuery]=useState("Technical founder in Berlin building AI infrastructure with enterprise traction.");
  const [chips,setChips]=useState(defaultChips);
  return <div>
    <section className="mb-6 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
      <div><div className="eyebrow mb-2">Intelligence workspace</div><h1 className="text-3xl font-bold tracking-tight text-ink">Founder discovery</h1><p className="mt-1.5 max-w-2xl text-sm text-muted">Evidence-backed signals from products, research, communities and founder-submitted material.</p></div>
      <button className="flex w-fit items-center gap-2 rounded-md bg-accent px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-slate-300"><Plus className="h-4 w-4"/>Add candidate</button>
    </section>

    <div className="mb-6 grid gap-3 sm:grid-cols-3">
      {[
        {icon:Users,label:"Active candidates",value:"128",hint:"+14 this week",tone:"bg-[#e8eef8] text-[#4e6f9e]",dot:"bg-[#6f8db7]"},
        {icon:Radar,label:"High thesis fit",value:"34",hint:"12 need review",tone:"bg-[#e7f3ef] text-[#38836e]",dot:"bg-[#4f9b84]"},
        {icon:TrendingUp,label:"New momentum",value:"18",hint:"Across 9 sources",tone:"bg-[#f0eafa] text-[#7656a5]",dot:"bg-[#8b6db6]"},
      ].map(({icon:Icon,label,value,hint,tone,dot})=><div key={label} className="panel flex items-center gap-4 rounded-lg border-t-2 border-t-transparent p-4 transition hover:border-t-current"><div className={`flex h-11 w-11 items-center justify-center rounded-lg ${tone}`}><Icon className="h-5 w-5"/></div><div><div className="flex items-center gap-2 text-xl font-bold">{value}<span className={`h-1.5 w-1.5 rounded-full ${dot}`}/></div><div className="text-xs font-medium text-ink-2">{label}</div></div><span className="ml-auto self-end text-[10px] text-muted">{hint}</span></div>)}
    </div>

    <section className="panel mb-6 rounded-lg p-5">
      <div className="mb-3 flex items-center gap-2"><Sparkles className="h-4 w-4 text-accent"/><span className="text-xs font-semibold text-accent">Natural-language thesis search</span></div>
      <div className="relative"><Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-2"/><input value={query} onChange={e=>setQuery(e.target.value)} className="w-full rounded-md border border-line bg-surface-2 py-3.5 pl-11 pr-4 text-sm outline-none focus:border-accent-muted"/></div>
      <div className="mt-4 flex flex-wrap items-center gap-2"><span className="text-[11px] font-medium text-muted">Interpreted as</span>{chips.map(c=><Chip key={c.id} {...c} onRemove={id=>setChips(v=>v.filter(x=>x.id!==id))}/>)}<button className="text-xs font-semibold text-accent">+ Add criterion</button></div>
    </section>

    <div className="mb-4 flex items-center justify-between"><div><h2 className="text-lg font-bold">Ranked candidates</h2><p className="text-xs text-muted">{candidates.length} profiles · Updated 3 minutes ago</p></div><button className="flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-semibold text-ink-2">Thesis fit <ChevronDown className="h-3.5 w-3.5"/></button></div>
    {isLoading && <div className="py-16 text-center text-sm text-muted">Building evidence-backed ranking…</div>}
    {error && !isLoading && <div className="mb-3 rounded-md bg-[#fff8ed] px-4 py-2.5 text-xs text-[#9a6a2d]">Live API is offline — showing the prepared demonstration cohort.</div>}
    {!isLoading && <div className="grid gap-4 xl:grid-cols-2">{candidates.map(c=><CandidateCard key={c.id} candidate={c} onViewFounder={()=>navigate(`/founders/${c.id}`)} onAddPipeline={()=>{}} />)}</div>}
  </div>;
}
