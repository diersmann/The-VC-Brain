import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { draftCandidateOutreach } from "../../api/candidates";
import type { Candidate } from "../../types/candidate";
import { OutreachComposer } from "./OutreachComposer";

vi.mock("../../api/candidates", () => ({
  draftCandidateOutreach: vi.fn(),
}));

const candidate: Candidate = {
  id: "candidate-1",
  stable_id: "candidate-1",
  display_name: "Ada Example",
  email: "ada@example.com",
  handles: null,
  consent_state: "granted",
  origin: "discovered",
  scores: null,
  latest_score_at: null,
  created_at: "2026-08-03T00:00:00Z",
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("OutreachComposer", () => {
  test("focuses the dialog, traps reverse tabbing, and closes on Escape", () => {
    const opener = document.createElement("button");
    document.body.append(opener);
    opener.focus();
    const onClose = vi.fn();

    render(<OutreachComposer candidate={candidate} onClose={onClose} />);

    const dialog = screen.getByRole("dialog");
    const closeButton = screen.getByRole("button", { name: "Close outreach composer" });
    expect(closeButton).toHaveFocus();

    fireEvent.keyDown(dialog, { key: "Tab", shiftKey: true });
    expect(screen.getByRole("button", { name: "Draft with email agent" })).toHaveFocus();

    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();
    opener.remove();
  });

  test("restores focus to the opener when the dialog unmounts", () => {
    const opener = document.createElement("button");
    document.body.append(opener);
    opener.focus();
    const onClose = vi.fn();
    const { unmount } = render(<OutreachComposer candidate={candidate} onClose={onClose} />);

    unmount();
    expect(opener).toHaveFocus();
    opener.remove();
  });

  test("keeps the draft action available for the mocked API path", async () => {
    vi.mocked(draftCandidateOutreach).mockResolvedValue({
      subject: "Hello",
      body: "Body",
      recipient_email: candidate.email,
      generation_mode: "template",
      model: null,
      warning: null,
    });
    render(<OutreachComposer candidate={candidate} onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Draft with email agent" }));
    expect(await screen.findByDisplayValue("Hello")).toBeInTheDocument();
    const handoff = screen.getByRole("link", { name: /Approve to hand off/ });
    expect(handoff).toHaveAttribute("aria-disabled", "true");
    expect(handoff).not.toHaveAttribute("href");
    fireEvent.click(screen.getByRole("checkbox", { name: /I approve this edited draft/ }));
    expect(screen.getByRole("link", { name: /Open in email/ })).toHaveAttribute("href", expect.stringContaining("mailto:"));

    fireEvent.change(screen.getByRole("textbox", { name: "Body" }), { target: { value: "Edited body" } });
    expect(screen.getByRole("link", { name: /Approve to hand off/ })).toHaveAttribute("aria-disabled", "true");
  });

  test("keeps manual handoff disabled for suppressed consent", async () => {
    vi.mocked(draftCandidateOutreach).mockResolvedValue({
      subject: "Hello",
      body: "Body",
      recipient_email: candidate.email,
      generation_mode: "template",
      model: null,
      warning: null,
    });
    render(<OutreachComposer candidate={{ ...candidate, consent_state: "suppressed" }} onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Draft with email agent" }));
    await screen.findByDisplayValue("Hello");

    expect(screen.getByText("Suppressed by consent state: suppressed. Manual email handoff is disabled.")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /I approve this edited draft/ })).toBeDisabled();
    expect(screen.queryByRole("link", { name: /Open in email/ })).not.toBeInTheDocument();
  });

  test("keeps an approved multiline draft actionable", async () => {
    vi.mocked(draftCandidateOutreach).mockResolvedValue({
      subject: "Hello",
      body: "Line one\nLine two",
      recipient_email: candidate.email,
      generation_mode: "template",
      model: null,
      warning: null,
    });
    render(<OutreachComposer candidate={candidate} onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Draft with email agent" }));
    await screen.findByDisplayValue("Hello");
    fireEvent.click(screen.getByRole("checkbox", { name: /I approve this edited draft/ }));

    expect(screen.getByRole("link", { name: "Open in email" })).toHaveAttribute("href", expect.stringContaining("%0A"));
  });

  test("invalidates approval when the recipient changes", async () => {
    vi.mocked(draftCandidateOutreach).mockResolvedValue({
      subject: "Hello",
      body: "Body",
      recipient_email: candidate.email,
      generation_mode: "template",
      model: null,
      warning: null,
    });
    const { rerender } = render(<OutreachComposer candidate={candidate} onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Draft with email agent" }));
    await screen.findByDisplayValue("Hello");
    fireEvent.click(screen.getByRole("checkbox", { name: /I approve this edited draft/ }));
    expect(screen.getByRole("link", { name: /Open in email/ })).toHaveAttribute("href", expect.stringContaining("ada@example.com"));

    rerender(<OutreachComposer candidate={{ ...candidate, email: "new@example.com" }} onClose={vi.fn()} />);
    expect(screen.getByRole("link", { name: /Approve to hand off/ })).not.toHaveAttribute("href");
  });
});
