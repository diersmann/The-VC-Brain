import { Outlet } from "react-router";
import { LeftNav } from "./LeftNav";

export function RootLayout() {
  return (
    <div className="min-h-screen">
      <div className="flex min-h-screen w-full bg-white/20">
        <LeftNav />
        <div className="min-w-0 flex-1">
          <main className="px-4 pb-8 pt-5 md:px-7 lg:px-9"><Outlet /></main>
        </div>
      </div>
    </div>
  );
}
