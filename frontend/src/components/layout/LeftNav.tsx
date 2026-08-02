import { useState } from "react";
import { NavLink } from "react-router";
import { Compass, Inbox, LayoutDashboard, SearchCheck, Scale } from "lucide-react";

const navItems = [
  { id: "home", label: "Overview", path: "/", icon: LayoutDashboard, color: "text-[#5277aa]" },
  { id: "inbound", label: "Inbound", path: "/inbound", icon: Inbox, color: "text-[#7656a5]" },
  { id: "sourcing", label: "Discover", path: "/sourcing", icon: Compass, color: "text-[#35816b]" },
  { id: "investigated", label: "Investigated", path: "/investigated", icon: SearchCheck, color: "text-[#5074a8]" },
  { id: "decisions", label: "Decisions", path: "/decisions", icon: Scale, color: "text-[#b18435]" },
];

export function LeftNav() {
  return (
    <aside className="sticky top-0 hidden h-screen w-[218px] shrink-0 flex-col overflow-y-auto bg-white/60 shadow-[12px_0_40px_rgba(70,91,120,.06)] backdrop-blur-2xl md:flex">
      <div className="px-7 py-8">
        <div className="brand-wordmark" aria-label="FirstCheck24">
          <span>FirstCheck</span><span className="brand-wordmark-number">24</span>
        </div>
        <div className="mt-1.5 text-[9px] font-semibold uppercase tracking-[.19em] text-muted-2">Investment intelligence</div>
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
        <div className="rounded-lg bg-white/60 p-3.5 shadow-[0_10px_28px_rgba(70,91,120,.07)] backdrop-blur-xl">
          <div className="mb-3 flex items-center gap-2"><div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#dce5f1] text-xs font-bold text-accent">SW</div><div><div className="text-xs font-semibold">Sophie Werner</div><div className="text-[11px] text-muted">Investment Partner</div></div></div>
          <div className="h-1.5 rounded-full bg-surface-3"><div className="h-full w-[72%] rounded-full bg-accent-muted" /></div>
          <div className="numeric mt-2 text-[11px] text-muted">12 of 18 candidates reviewed</div>
        </div>
      </div>
    </aside>
  );
}

export function MobileNav() {
  const [open, setOpen] = useState(false);

  return (
    <div className="border-b border-line bg-white/80 px-4 py-3 shadow-sm backdrop-blur-xl md:hidden">
      <div className="flex items-center justify-between gap-3">
        <div className="brand-wordmark" aria-label="FirstCheck24">
          <span>FirstCheck</span><span className="brand-wordmark-number">24</span>
        </div>
        <button
          type="button"
          aria-expanded={open}
          aria-controls="mobile-workspace-nav"
          aria-label={open ? "Close workspace navigation" : "Open workspace navigation"}
          onClick={() => setOpen((current) => !current)}
          className="rounded-md border border-line bg-white px-3 py-2 text-xs font-bold text-ink-2 shadow-sm"
        >
          {open ? "Close" : "Menu"}
        </button>
      </div>
      {open && (
        <nav id="mobile-workspace-nav" aria-label="Mobile workspace" className="mt-3 grid gap-1.5 border-t border-line pt-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            return <NavLink key={item.id} to={item.path} onClick={() => setOpen(false)} className={({ isActive }) => `flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium ${isActive ? "bg-accent text-white" : "text-muted hover:bg-surface-2 hover:text-ink"}`}><Icon className="h-4 w-4" />{item.label}</NavLink>;
          })}
        </nav>
      )}
    </div>
  );
}
