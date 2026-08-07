import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import App from "./App";

const initialUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;

afterEach(() => {
  cleanup();
  window.history.replaceState({}, "", initialUrl);
});

describe("App routing", () => {
  it("keeps unknown paths on the dedicated 404 page", async () => {
    window.history.pushState({}, "", "/definitely-not-a-workspace-route");

    render(<App />);

    expect(await screen.findByText("That workspace does not exist.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to workspace" })).toHaveAttribute("href", "/");
  });
});
