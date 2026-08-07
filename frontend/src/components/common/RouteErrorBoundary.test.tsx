import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RouteErrorBoundary } from "./RouteErrorBoundary";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("RouteErrorBoundary", () => {
  it("redacts render errors and can retry the failed route", () => {
    let shouldThrow = true;
    const onRetry = vi.fn();

    function SecretBearingRoute() {
      if (shouldThrow) {
        throw new Error("secret-token=do-not-render");
      }

      return <p>Route recovered</p>;
    }

    vi.spyOn(console, "error").mockImplementation(() => undefined);

    render(
      <MemoryRouter>
        <RouteErrorBoundary onRetry={onRetry}>
          <SecretBearingRoute />
        </RouteErrorBoundary>
      </MemoryRouter>,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "We couldn’t load this page." })).toBeInTheDocument();
    expect(screen.queryByText("secret-token=do-not-render")).not.toBeInTheDocument();

    shouldThrow = false;
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(onRetry).toHaveBeenCalledOnce();
    expect(screen.getByText("Route recovered")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("offers a navigation-safe workspace fallback", () => {
    const shouldThrow = true;

    function FailingRoute() {
      if (shouldThrow) {
        throw new Error("private failure details");
      }

      return <p>Recovered</p>;
    }

    vi.spyOn(console, "error").mockImplementation(() => undefined);

    render(
      <MemoryRouter>
        <main id="main-content">
          <RouteErrorBoundary embedded>
            <FailingRoute />
          </RouteErrorBoundary>
        </main>
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Back to workspace" })).toHaveAttribute("href", "/");
    expect(screen.getAllByRole("main")).toHaveLength(1);
    expect(screen.queryByText("private failure details")).not.toBeInTheDocument();
  });

  it("resets the boundary when fallback navigation changes routes", () => {
    function FailingRoute(): never {
      throw new Error("route-only-private-details");
    }

    vi.spyOn(console, "error").mockImplementation(() => undefined);

    render(
      <MemoryRouter initialEntries={["/broken"]}>
        <RouteErrorBoundary>
          <Routes>
            <Route path="/broken" element={<FailingRoute />} />
            <Route path="/" element={<p>Workspace home</p>} />
          </Routes>
        </RouteErrorBoundary>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("link", { name: "Back to workspace" }));

    expect(screen.getByText("Workspace home")).toBeInTheDocument();
    expect(screen.queryByText("route-only-private-details")).not.toBeInTheDocument();
  });
});
