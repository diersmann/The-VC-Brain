import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";

import { TestQueryProvider } from "../test/queryClient";
import { OpportunityInboxPage } from "./OpportunityInboxPage";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const candidates = [
  {
    id: "inbound-1",
    stable_id: "inbound-1",
    display_name: "Alice Example",
    email: null,
    handles: null,
    consent_state: "pending",
    origin: "inbound",
    lifecycle_stage: "received",
    scores: null,
    profile: { company: "Aperture AI", source_types: ["inbound_deck"] },
    sla: { status: "at_risk", alert: true, alert_level: "warning", owner: null },
  },
  {
    id: "outbound-1",
    stable_id: "outbound-1",
    display_name: "Bob Example",
    email: null,
    handles: { github: "bob" },
    consent_state: "granted",
    origin: "outbound",
    lifecycle_stage: "memo_ready",
    scores: { founder: 0.8 },
    thesis_match: { score: 0.8 },
    profile: { company: "Northstar Labs", source_types: ["github"] },
    sla: { status: "on_track", alert: false, alert_level: "none", owner: "team" },
  },
];

describe("OpportunityInboxPage", () => {
  it("shows unified stages, SLA ownership, actions, and saved attention view", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(candidates), { status: 200 })));
    render(<TestQueryProvider><MemoryRouter initialEntries={["/inbox"]}><OpportunityInboxPage /></MemoryRouter></TestQueryProvider>);

    expect(await screen.findByText("Alice Example")).toBeInTheDocument();
    expect(screen.getByText("Triage submission")).toBeInTheDocument();
    expect(screen.getByText("Owner unavailable")).toBeInTheDocument();
    expect(screen.getByText("Record decision")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Saved view"), { target: { value: "attention" } });
    expect(await screen.findByText("Alice Example")).toBeInTheDocument();
    expect(screen.queryByText("Bob Example")).not.toBeInTheDocument();
  });
});
