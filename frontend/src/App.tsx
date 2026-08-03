import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { RootLayout } from "./components/layout/RootLayout";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { NotFoundPage } from "./pages/NotFoundPage";

const SourcingPage = lazy(() => import("./components/sourcing/SourcingPage").then((module) => ({ default: module.SourcingPage })));
const FounderProfilePage = lazy(() => import("./pages/FounderProfilePage").then((module) => ({ default: module.FounderProfilePage })));
const OnboardingPage = lazy(() => import("./pages/OnboardingPage").then((module) => ({ default: module.OnboardingPage })));
const HomePage = lazy(() => import("./pages/HomePage").then((module) => ({ default: module.HomePage })));
const DecisionQueuePage = lazy(() => import("./pages/DecisionQueuePage").then((module) => ({ default: module.DecisionQueuePage })));
const DecisionDetailPage = lazy(() => import("./pages/DecisionDetailPage").then((module) => ({ default: module.DecisionDetailPage })));
const InboundInboxPage = lazy(() => import("./pages/InboundInboxPage").then((module) => ({ default: module.InboundInboxPage })));
const OpportunityInboxPage = lazy(() => import("./pages/OpportunityInboxPage").then((module) => ({ default: module.OpportunityInboxPage })));
const InvestigatedPage = lazy(() => import("./pages/InvestigatedPage").then((module) => ({ default: module.InvestigatedPage })));
const PitchSubmissionPage = lazy(() => import("./pages/PitchSubmissionPage").then((module) => ({ default: module.PitchSubmissionPage })));

function RouteLoading() {
  return <div className="flex min-h-[60vh] items-center justify-center text-sm text-muted">Loading workspace…</div>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<RouteLoading />}>
        <Routes>
          <Route path="apply" element={<Navigate to="/submit" replace />} />
          <Route path="submit" element={<PitchSubmissionPage />} />
          <Route element={<RootLayout />}>
            <Route index element={<HomePage />} />
            <Route path="sourcing" element={<SourcingPage />} />
            <Route path="investigated" element={<InvestigatedPage />} />
            <Route path="inbound" element={<InboundInboxPage />} />
            <Route path="inbox" element={<OpportunityInboxPage />} />
            <Route path="decisions" element={<DecisionQueuePage />} />
            <Route path="decisions/:founderId" element={<DecisionDetailPage />} />
            <Route path="founders/:founderId" element={<FounderProfilePage />} />
            <Route path="onboarding" element={<OnboardingPage />} />
            <Route path="memos" element={<PlaceholderPage label="Memos" />} />
            <Route path="thesis" element={<OnboardingPage />} />
            <Route path="settings" element={<PlaceholderPage label="Settings" />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
