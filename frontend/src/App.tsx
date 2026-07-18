import { useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { RootLayout } from "./components/layout/RootLayout";
import { SourcingPage } from "./components/sourcing/SourcingPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";

export default function App() {
  const [pendingApprovals] = useState(3);

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<RootLayout pendingApprovals={pendingApprovals} />}>
          <Route index element={<Navigate to="/sourcing" replace />} />
          <Route path="sourcing" element={<SourcingPage />} />
          <Route path="memos" element={<PlaceholderPage label="Memos" />} />
          <Route path="thesis" element={<PlaceholderPage label="Thesis" />} />
          <Route path="settings" element={<PlaceholderPage label="Settings" />} />
          <Route path="*" element={<PlaceholderPage label="Not Found" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
