import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { RootLayout } from "./components/layout/RootLayout";
import { SourcingPage } from "./components/sourcing/SourcingPage";
import { FounderProfilePage } from "./pages/FounderProfilePage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { HomePage } from "./pages/HomePage";
import { DecisionQueuePage } from "./pages/DecisionQueuePage";
import { DecisionDetailPage } from "./pages/DecisionDetailPage";
import { InboundInboxPage } from "./pages/InboundInboxPage";
import { InvestigatedPage } from "./pages/InvestigatedPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { PitchSubmissionPage } from "./pages/PitchSubmissionPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="apply" element={<Navigate to="/submit" replace />} />
        <Route path="submit" element={<PitchSubmissionPage />} />
        <Route element={<RootLayout />}>
          <Route index element={<HomePage />} />
          <Route path="sourcing" element={<SourcingPage />} />
          <Route path="investigated" element={<InvestigatedPage />} />
          <Route path="inbound" element={<InboundInboxPage />} />
          <Route path="decisions" element={<DecisionQueuePage />} />
          <Route path="decisions/:founderId" element={<DecisionDetailPage />} />
          <Route path="founders/:founderId" element={<FounderProfilePage />} />
          <Route path="onboarding" element={<OnboardingPage />} />
          <Route path="memos" element={<PlaceholderPage label="Memos" />} />
          <Route path="thesis" element={<OnboardingPage />} />
          <Route path="settings" element={<PlaceholderPage label="Settings" />} />
          <Route path="*" element={<PlaceholderPage label="Not Found" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
