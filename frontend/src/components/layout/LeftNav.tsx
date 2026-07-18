import { NavLink } from "react-router";
import { Compass, Sparkles, Inbox, LayoutDashboard, Scale } from "lucide-react";

const navItems = [
  { id: "home", label: "Overview", path: "/", icon: LayoutDashboard, color: "text-[#5277aa]" },
  { id: "inbound", label: "Inbound", path: "/inbound", icon: Inbox, color: "text-[#7656a5]" },
  { id: "sourcing", label: "Discover", path: "/sourcing", icon: Compass, color: "text-[#35816b]" },
  { id: "decisions", label: "Decisions", path: "/decisions", icon: Scale, color: "text-[#b18435]" },
];

export function LeftNav() {
  return (
    <aside className="hidden w-[218px] shrink-0 flex-col border-r border-line bg-white/75 md:flex">
      <div className="flex items-center gap-3 px-6 py-7">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-white shadow-lg shadow-slate-300"><Sparkles className="h-5 w-5" /></div>
        <div><div className="font-bold tracking-tight">The VC Brain</div><div className="text-[10px] font-semibold uppercase tracking-[.16em] text-muted-2">Founder intelligence</div></div>
      </div>
      <div className="px-4 py-3">
        <div className="eyebrow px-3 pb-3">Workspace</div>
        <nav className="space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            return <NavLink key={item.id} to={item.path} className={({isActive}) => `flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition ${isActive ? "bg-accent text-white shadow-md shadow-slate-200" : "text-muted hover:bg-surface-2 hover:text-ink"}`}>{({isActive})=><><Icon className={`h-4 w-4 ${isActive?"text-white":item.color}`} />{item.label}</>}</NavLink>;
          })}
        </nav>
      </div>
      <div className="mt-auto p-4">
        <div className="rounded-lg bg-surface-2 p-3.5">
          <div className="mb-3 flex items-center gap-2"><div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#dce5f1] text-xs font-bold text-accent">SW</div><div><div className="text-xs font-semibold">Sophie Werner</div><div className="text-[11px] text-muted">Investment Partner</div></div></div>
          <div className="h-1.5 rounded-full bg-surface-3"><div className="h-full w-[72%] rounded-full bg-accent-muted" /></div>
          <div className="mt-2 text-[10px] text-muted">12 of 18 candidates reviewed</div>
        </div>
      </div>
    </aside>
  );
}
