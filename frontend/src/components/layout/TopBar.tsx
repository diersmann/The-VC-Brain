import { useState } from "react";
import { useNavigate } from "react-router";
import { Search, Bell, CheckSquare, ChevronDown, Command, X } from "lucide-react";

interface TopBarProps {
  pendingApprovals: number;
}

export function TopBar({ pendingApprovals }: TopBarProps) {
  const navigate = useNavigate();
  const [searchValue, setSearchValue] = useState("");
  const [searchFocused, setSearchFocused] = useState(false);

  return (
    <header className="sticky top-0 h-14 flex items-center gap-4 px-6 border-b border-line bg-canvas z-30">
      {/* Global Search */}
      <div className="relative flex-1 max-w-[480px]">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-2" />
        <input
          type="text"
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          onFocus={() => setSearchFocused(true)}
          onBlur={() => setSearchFocused(false)}
          placeholder="Search founders, companies, signals..."
          className={`w-full pl-9 pr-9 py-1.5 text-sm rounded-md border outline-none transition-colors placeholder:text-muted-2 bg-surface text-ink ${
            searchFocused ? "border-accent" : "border-line"
          }`}
        />
        {searchValue && (
          <button
            onClick={() => setSearchValue("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-2 hover:text-ink"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Thesis Selector */}
      <button className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-line text-sm text-ink bg-surface hover:border-line-2 transition-colors">
        <div className="w-2 h-2 rounded-full bg-accent" />
        <span className="max-w-[200px] truncate">Series A Focus — Berlin Deep Tech</span>
        <ChevronDown className="w-3.5 h-3.5 text-muted-2 flex-shrink-0" />
      </button>

      <div className="flex-1" />

      {/* Keyboard shortcut hint */}
      <button className="flex items-center gap-1.5 px-2 py-1 rounded text-xs border border-line text-muted-2 hover:border-line-2">
        <Command className="w-3 h-3" />
        <span>K</span>
      </button>

      {/* Notifications */}
      <button className="relative w-8 h-8 flex items-center justify-center rounded-md hover:bg-surface-2 transition-colors">
        <Bell className="w-4 h-4 text-muted" />
        <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-accent" />
      </button>

      {/* Pending Approvals */}
      <button
        onClick={() => navigate("/memos")}
        className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm text-white bg-warn hover:opacity-90 transition-colors"
      >
        <CheckSquare className="w-3.5 h-3.5" />
        <span>{pendingApprovals} pending approval{pendingApprovals !== 1 ? "s" : ""}</span>
      </button>
    </header>
  );
}
