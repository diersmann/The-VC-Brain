import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import { MemoryRouter } from "react-router";

import { LeftNav, MobileNav } from "./LeftNav";
import { RootLayout } from "./RootLayout";

afterEach(cleanup);

describe("workspace navigation", () => {
  test("exposes the mobile workspace routes behind an accessible menu", () => {
    render(<MemoryRouter><MobileNav /></MemoryRouter>);

    const trigger = screen.getByRole("button", { name: "Open workspace navigation" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(trigger);

    expect(screen.getByRole("navigation", { name: "Mobile workspace" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Discover" })).toHaveAttribute("href", "/sourcing");
    expect(screen.getByRole("link", { name: "Decisions" })).toHaveAttribute("href", "/decisions");
    fireEvent.click(screen.getByRole("link", { name: "Discover" }));
    expect(screen.getByRole("button", { name: "Open workspace navigation" })).toHaveAttribute("aria-expanded", "false");
  });

  test("provides a skip link and a single main landmark in the shell", () => {
    render(<MemoryRouter><RootLayout /></MemoryRouter>);

    const skipLink = screen.getByRole("link", { name: "Skip to main content" });
    expect(skipLink).toHaveAttribute("href", "#main-content");
    expect(screen.getAllByRole("main")).toHaveLength(1);
    const main = screen.getByRole("main");
    expect(main).toHaveAttribute("id", "main-content");
    expect(main).toHaveAttribute("tabindex", "-1");

    fireEvent.click(skipLink);
    expect(main).toHaveFocus();
  });

  test("keeps the desktop navigation available", () => {
    render(<MemoryRouter><LeftNav /></MemoryRouter>);
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Investigated" })).toHaveAttribute("href", "/investigated");
    expect(screen.getByText("Demo workspace")).toBeInTheDocument();
    expect(screen.getByText(/Review workload is unavailable/)).toBeInTheDocument();
  });
});
