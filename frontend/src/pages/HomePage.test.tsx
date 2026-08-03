import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";

import { HomePage } from "./HomePage";
import { TestQueryProvider } from "../test/queryClient";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function renderHome() {
  return render(
    <TestQueryProvider>
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    </TestQueryProvider>,
  );
}

function response(body: unknown, status = 200) {
  return new Response(body === null ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("HomePage data states", () => {
  it("does not render zero-valued investment metrics when the pipeline fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: unknown) => String(input).includes("candidates") ? Promise.resolve(response(null, 500)) : Promise.resolve(response(null, 404))),
    );

    renderHome();

    expect(await screen.findByRole("alert")).toHaveTextContent("Investment data unavailable");
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByText("Scoring coverage")).not.toBeInTheDocument();
    expect(screen.getByText(/no investment conclusion was inferred/i)).toBeInTheDocument();
  });

  it("keeps an empty pipeline distinct from a failed request and supports retry", async () => {
    let candidateAttempts = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn((input: unknown) => {
        if (String(input).includes("candidates")) {
          candidateAttempts += 1;
          return Promise.resolve(candidateAttempts === 1 ? response(null, 500) : response([]));
        }
        return Promise.resolve(response(null, 404));
      }),
    );

    renderHome();
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => expect(screen.getByText("No live candidates yet.")).toBeInTheDocument());
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText("No active thesis is configured. This is an empty configuration state, not a score.")).toBeInTheDocument();
  });

  it("shows a permission failure as a partial state when pipeline data is available", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: unknown) => String(input).includes("candidates") ? Promise.resolve(response([])) : Promise.resolve(response(null, 403))),
    );

    renderHome();

    expect(await screen.findByText("Permission required")).toBeInTheDocument();
    expect(screen.getAllByText("Thesis unavailable")).toHaveLength(2);
    expect(screen.getByText("No live candidates yet.")).toBeInTheDocument();
  });
});
