import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

import type { FounderProfile } from "../../types/profile";
import { FounderProfileInsights } from "./FounderProfileInsights";

afterEach(cleanup);

const profile: FounderProfile = {
  stableId: "founder-1",
  initials: "TF",
  company: "Example Labs",
  role: "Founder",
  location: "Berlin",
  stage: "Investigating",
  sector: "AI infrastructure",
  summary: "A founder building reliable infrastructure.",
  signal: "Public activity signal: 120 stars",
  tags: ["GitHub", "Research"],
  founderScore: 82,
  momentum: 75,
  thesisFit: 80,
  evidence: 70,
  sourceConfidence: 70,
  coverageScore: 64,
  scoreHint: "4 observations across 2 sources",
  assessments: [],
  events: [{ date: "Jan 2, 2025", title: "Github Bio", body: "Building infrastructure.", type: "Github", trust: 85 }],
  claims: [],
  coverage: [{ label: "Identity & background", value: 80 }, { label: "Market evidence", value: 40 }],
  gaps: ["Customer references are missing"],
  relations: [{ label: "Example Partner", sub: "Former colleague", kind: "person", verified: true }, { label: "Possible advisor", sub: "Inferred link", kind: "person", verified: false }],
  affiliations: [{ name: "Example Labs", role: "Founder", meta: "Investigating · github", kind: "company" }],
  trendHistory: [62, 74, 82],
  axisTrendHistory: { Founder: [82], Market: [70], "Idea × Market": [80] },
};

describe("FounderProfileInsights", () => {
  test("renders score history, evidence coverage, gaps, and relationship semantics", () => {
    render(<FounderProfileInsights profile={profile} />);

    expect(screen.getByRole("heading", { name: "What the current evidence says" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Founder score history" })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Evidence timeline" })).toHaveTextContent("Github Bio");
    expect(screen.getByRole("progressbar", { name: "Identity & background coverage" })).toHaveAttribute("aria-valuenow", "80");
    expect(screen.getByText(/Customer references are missing/)).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
    expect(screen.getByText("Needs verification")).toBeInTheDocument();
  });
});
