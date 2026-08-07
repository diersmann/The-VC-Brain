import { Outlet } from "react-router";
import { RouteErrorBoundary } from "../common/RouteErrorBoundary";
import { retryRoute } from "../common/routeRetry";
import { LeftNav, MobileNav } from "./LeftNav";

export function RootLayout() {
  return (
    <div className="min-h-screen">
      <a
        href="#main-content"
        onClick={(event) => {
          const main = document.getElementById("main-content");
          if (!main) return;
          event.preventDefault();
          main.focus();
        }}
        className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[100] focus:rounded-md focus:bg-accent focus:px-4 focus:py-3 focus:text-sm focus:font-bold focus:text-white"
      >
        Skip to main content
      </a>
      <MobileNav />
      <div className="flex min-h-screen w-full bg-white/20">
        <LeftNav />
        <div className="min-w-0 flex-1">
          <main id="main-content" tabIndex={-1} className="px-4 pb-8 pt-5 md:px-7 lg:px-9">
            <RouteErrorBoundary embedded onRetry={retryRoute}><Outlet /></RouteErrorBoundary>
          </main>
        </div>
      </div>
    </div>
  );
}
