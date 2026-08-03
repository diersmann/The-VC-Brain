import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";

import { InboundInboxPage } from "./InboundInboxPage";
import { TestQueryProvider } from "../test/queryClient";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const candidates = [
  {
    id: "candidate-1",
    stable_id: "alice-001",
    display_name: "Alice Example",
    email: "alice@example.com",
    handles: { linkedin: "alice-example" },
    consent_state: "granted",
    origin: "inbound",
    profile: { company: "Aperture AI", deck_title: "Aperture seed deck", deck_url: null, source_types: ["inbound_deck"] },
    scores: null,
    created_at: "2026-07-01T10:00:00Z",
    latest_score_at: null,
  },
  {
    id: "candidate-2",
    stable_id: "bob-002",
    display_name: "Bob Example",
    email: "bob@example.com",
    handles: { github: "bob-example" },
    consent_state: "granted",
    origin: "inbound",
    profile: { company: "Northstar Labs", deck_title: "Northstar deck", deck_url: null, source_types: ["inbound_deck"] },
    scores: null,
    created_at: "2026-07-02T10:00:00Z",
    latest_score_at: null,
  },
];

function renderInbox(initialEntry = "/inbound?q=aperture") {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(candidates), { status: 200 })));
  return render(<TestQueryProvider><MemoryRouter initialEntries={[initialEntry]}><InboundInboxPage /></MemoryRouter></TestQueryProvider>);
}

describe("InboundInboxPage search states", () => {
  it("searches URL state across company fields and keeps global counts", async () => {
    renderInbox();

    expect(await screen.findByText("Alice Example")).toBeInTheDocument();
    expect(screen.queryByText("Bob Example")).not.toBeInTheDocument();
    expect(screen.getByText("Showing 1 of 2 inbound applications")).toBeInTheDocument();
    expect(screen.getAllByText("2", { selector: ".numeric" })).toHaveLength(2);

    fireEvent.click(screen.getByRole("button", { name: "Clear search" }));
    expect(await screen.findByText("Bob Example")).toBeInTheDocument();
  });

  it("distinguishes no matching applications from an empty inbox", async () => {
    renderInbox("/inbound?q=missing");

    expect(await screen.findByText('No applications match “missing”')).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Clear search" })).toHaveLength(2);
  });
});
