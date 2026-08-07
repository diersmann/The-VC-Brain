import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { SafeLink } from "./SafeLink";

afterEach(cleanup);

describe("SafeLink", () => {
  it("renders HTTP destinations with a forced safe external target", () => {
    render(<SafeLink href="https://example.com/source">Open source</SafeLink>);

    const link = screen.getByRole("link", { name: "Open source" });
    expect(link).toHaveAttribute("href", "https://example.com/source");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noreferrer");
  });

  it("keeps approved mailto actions actionable without external-window attributes", () => {
    render(<SafeLink href="mailto:ada@example.com?subject=Hello%20there&body=Line%20one" allowMailto>Open in email</SafeLink>);

    const link = screen.getByRole("link", { name: "Open in email" });
    expect(link).toHaveAttribute("href", "mailto:ada@example.com?subject=Hello%20there&body=Line%20one");
    expect(link).not.toHaveAttribute("target");
    expect(link).not.toHaveAttribute("rel");
  });

  it.each([
    "javascript:alert(1)",
    "data:text/html,unsafe",
    "mailto:ada@example.com?bcc=attacker@example.com",
  ])("does not render unsupported action %s", (href) => {
    render(<SafeLink href={href} allowMailto>Unsafe action</SafeLink>);
    expect(screen.queryByRole("link", { name: "Unsafe action" })).not.toBeInTheDocument();
  });
});
