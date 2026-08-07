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

function renderInbox(initialEntry = "/inbound?q=aperture", body: unknown = candidates) {
  vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))));
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

  it("uses the envelope total for database-wide application counts", async () => {
    renderInbox("/inbound", {
      version: "v1",
      items: candidates,
      next_cursor: "next-page",
      total_count: 250,
      limit: 200,
      search: null,
      filters: { origin: "inbound" },
    });

    expect(await screen.findByText("250")).toBeInTheDocument();
    expect(screen.getByText("Showing 2 of 250 inbound applications")).toBeInTheDocument();
    expect(screen.getByText("2 loaded of 250 total")).toBeInTheDocument();
  });

  it("loads the next cursor only after an explicit request", async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      const hasCursor = url.includes("cursor=next-page");
      const page = hasCursor
        ? {
            version: "v1",
            items: [candidates[1]],
            next_cursor: null,
            total_count: 2,
            limit: 1,
            search: null,
            filters: { origin: "inbound" },
          }
        : {
            version: "v1",
            items: [candidates[0]],
            next_cursor: "next-page",
            total_count: 2,
            limit: 1,
            search: null,
            filters: { origin: "inbound" },
          };
      return Promise.resolve(new Response(JSON.stringify(page), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<TestQueryProvider><MemoryRouter initialEntries={["/inbound"]}><InboundInboxPage /></MemoryRouter></TestQueryProvider>);
    expect(await screen.findByText("Alice Example")).toBeInTheDocument();
    expect(screen.queryByText("Bob Example")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Load more inbound applications/ }));
    expect(await screen.findByText("Bob Example")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("cursor=next-page"))).toBe(true);
    expect(screen.queryByRole("button", { name: /Load more inbound applications/ })).not.toBeInTheDocument();
  });

  it("keeps a v1 server match whose evidence is outside the candidate DTO", async () => {
    const evidenceMatch = {
      ...candidates[0],
      id: "candidate-evidence",
      display_name: "Evidence Match",
      profile: { company: "Opaque Labs", deck_title: null, deck_url: null, source_types: [] },
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);
        const isSearch = url.includes("search=retention");
        const page = {
          version: "v1",
          items: isSearch ? [evidenceMatch] : [evidenceMatch],
          next_cursor: null,
          total_count: 1,
          limit: 1,
          search: isSearch ? "retention" : null,
          filters: { origin: "inbound" },
        };
        return Promise.resolve(new Response(JSON.stringify(page), { status: 200 }));
      }),
    );

    render(<TestQueryProvider><MemoryRouter initialEntries={["/inbound?q=retention"]}><InboundInboxPage /></MemoryRouter></TestQueryProvider>);
    expect(await screen.findByText("Evidence Match")).toBeInTheDocument();
  });
});
