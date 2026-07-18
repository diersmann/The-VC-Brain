import { NavLink } from "react-router";
import { Zap, FileText, Target, Settings } from "lucide-react";

interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { id: "sourcing", label: "Sourcing", path: "/sourcing", icon: Zap },
  { id: "memo", label: "Memos", path: "/memos", icon: FileText },
  { id: "thesis", label: "Thesis", path: "/thesis", icon: Target },
  { id: "settings", label: "Settings", path: "/settings", icon: Settings },
];

export function LeftNav() {
  return (
    <nav className="fixed left-0 top-0 h-screen w-[220px] flex flex-col border-r border-line bg-canvas z-40">
      {/* Logo */}
      <div className="flex items-center gap-2 px-5 py-4 border-b border-line">
        <div className="w-7 h-7 rounded-md flex items-center justify-center bg-accent">
          <Zap className="w-3.5 h-3.5 text-white" />
        </div>
        <span className="tracking-tight text-ink">
          VC <span className="text-accent">Brain</span>
        </span>
      </div>

      {/* Nav Items */}
      <div className="flex-1 py-3 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.id}
              to={item.path}
              className={({ isActive }) =>
                `w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors relative ${
                  isActive
                    ? "bg-accent-soft text-accent"
                    : "text-muted hover:text-ink hover:bg-surface-2"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <div className="absolute left-0 top-1 bottom-1 w-0.5 rounded-r bg-accent" />
                  )}
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span className="text-sm">{item.label}</span>
                </>
              )}
            </NavLink>
          );
        })}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-line">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs bg-ink">
            SW
          </div>
          <div>
            <div className="text-xs text-ink">Sophie Werner</div>
            <div className="text-xs text-muted-2">Partner</div>
          </div>
        </div>
      </div>
    </nav>
  );
}
