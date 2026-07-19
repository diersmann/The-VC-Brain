import { Outlet } from "react-router";
import { LeftNav } from "./LeftNav";
import { TopBar } from "./TopBar";

interface RootLayoutProps { pendingApprovals: number; }

export function RootLayout({ pendingApprovals }: RootLayoutProps) {
  return (
    <div className="min-h-screen">
      <div className="flex min-h-screen w-full bg-white/20">
        <LeftNav />
        <div className="min-w-0 flex-1">
          <TopBar pendingApprovals={pendingApprovals} />
          <main className="px-4 pb-8 pt-5 md:px-7 lg:px-9"><Outlet /></main>
        </div>
      </div>
    </div>
  );
}
