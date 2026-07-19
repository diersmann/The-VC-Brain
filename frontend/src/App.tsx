import { BrowserRouter, Route, Routes } from "react-router";
import { RootLayout } from "./components/layout/RootLayout";
import { SourcingPage } from "./components/sourcing/SourcingPage";
import { FounderProfilePage } from "./pages/FounderProfilePage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { HomePage } from "./pages/HomePage";
import { InboundPage } from "./pages/InboundPage";
import { DecisionQueuePage } from "./pages/DecisionQueuePage";
import { DecisionDetailPage } from "./pages/DecisionDetailPage";
import { InboundInboxPage } from "./pages/InboundInboxPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="apply" element={<InboundPage />} />
        <Route element={<RootLayout />}>
          <Route index element={<HomePage />} />
          <Route path="sourcing" element={<SourcingPage />} />
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
