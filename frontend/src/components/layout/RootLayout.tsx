import { Outlet } from "react-router";
import { LeftNav } from "./LeftNav";
import { TopBar } from "./TopBar";

interface RootLayoutProps {
  pendingApprovals: number;
}

export function RootLayout({ pendingApprovals }: RootLayoutProps) {
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <LeftNav />
      <div className="ml-[220px]">
        <TopBar pendingApprovals={pendingApprovals} />
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
