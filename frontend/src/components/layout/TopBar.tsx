import { useState } from "react";
import { useNavigate } from "react-router";
import { Search, Bell, ChevronDown, SlidersHorizontal } from "lucide-react";

interface TopBarProps { pendingApprovals: number; }
export function TopBar({ pendingApprovals }: TopBarProps) {
  const navigate = useNavigate(); const [search, setSearch] = useState("");
  return <header className="sticky top-0 z-30 flex h-[76px] items-center gap-3 bg-white/65 px-4 shadow-[0_10px_32px_rgba(70,91,120,.06)] backdrop-blur-2xl md:px-7 lg:px-9">
    <div className="relative max-w-[470px] flex-1"><Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-2" /><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search founders, companies, signals..." className="w-full rounded-md bg-white/70 py-2.5 pl-11 pr-4 text-sm shadow-inner shadow-slate-200/60 outline-none transition focus:bg-white focus:ring-2 focus:ring-accent/10" /></div>
    <button className="hidden items-center gap-2 rounded-md bg-white/70 px-3.5 py-2 text-xs font-medium text-ink-2 shadow-sm lg:flex"><span className="h-2 w-2 rounded-full bg-success" />Berlin Deep Tech <ChevronDown className="h-3.5 w-3.5 text-muted" /></button>
    <button className="relative flex h-10 w-10 items-center justify-center rounded-md bg-white/70 text-muted shadow-sm"><Bell className="h-4 w-4"/><span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-danger" /></button>
    <button onClick={()=>navigate('/memos')} className="hidden items-center gap-2 rounded-md bg-accent px-4 py-2.5 text-xs font-semibold text-white sm:flex"><SlidersHorizontal className="h-4 w-4"/>{pendingApprovals} reviews</button>
  </header>;
}
