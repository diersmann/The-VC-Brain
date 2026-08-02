import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import { NotFoundPage } from "./NotFoundPage";

describe("NotFoundPage", () => {
  it("offers a useful recovery path", () => {
    render(<MemoryRouter><NotFoundPage /></MemoryRouter>);

    expect(screen.getByText("That workspace does not exist.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to workspace" })).toHaveAttribute("href", "/");
  });
});
