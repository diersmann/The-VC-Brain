import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PitchSubmissionPage } from "./PitchSubmissionPage";
import { submitPitch } from "../api/inbound";

vi.mock("../api/inbound", () => ({
  submitPitch: vi.fn(),
}));

const mockedSubmitPitch = vi.mocked(submitPitch);

function chooseDeck() {
  const deck = new File(["%PDF-1.7"], "pitch.pdf", { type: "application/pdf" });
  const input = document.querySelector('input[type="file"]');
  if (!(input instanceof HTMLInputElement)) throw new Error("Deck input not found");
  fireEvent.change(input, { target: { files: [deck] } });
}

describe("PitchSubmissionPage", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    mockedSubmitPitch.mockReset();
  });

  it("shows the persisted opportunity ID after a successful submission", async () => {
    mockedSubmitPitch.mockResolvedValue({
      status: "success",
      person_id: "person-1",
      opportunity_id: "opportunity-1",
    });

    render(<PitchSubmissionPage />);
    expect(screen.getByLabelText(/Founder name/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Email address/)).toBeInTheDocument();
    expect(screen.getByText(/used only for investment review/i)).toBeInTheDocument();
    fireEvent.input(screen.getByPlaceholderText("Your full name"), { target: { value: "Alice Example" } });
    fireEvent.input(screen.getByPlaceholderText("you@company.com"), { target: { value: "alice@example.com" } });
    fireEvent.input(screen.getByPlaceholderText("Your company or project"), { target: { value: "Example AI" } });
    chooseDeck();
    fireEvent.submit(screen.getByRole("button", { name: "Submit application" }).closest("form")!);

    expect(await screen.findByText("Application received")).toBeInTheDocument();
    expect(screen.getByTestId("submission-id")).toHaveTextContent("opportunity-1");
  });

  it("keeps the form and displays an error when submission fails", async () => {
    mockedSubmitPitch.mockRejectedValue(new Error("network failure"));

    render(<PitchSubmissionPage />);
    fireEvent.input(screen.getByPlaceholderText("Your full name"), { target: { value: "Alice Example" } });
    fireEvent.input(screen.getByPlaceholderText("you@company.com"), { target: { value: "alice@example.com" } });
    fireEvent.input(screen.getByPlaceholderText("Your company or project"), { target: { value: "Example AI" } });
    chooseDeck();
    fireEvent.submit(screen.getByRole("button", { name: "Submit application" }).closest("form")!);

    expect(await screen.findByRole("alert")).toHaveTextContent("could not submit");
    expect(screen.queryByText("Application received")).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByPlaceholderText("Your company or project")).toHaveValue("Example AI"));
  });

  it("resets all form fields and the deck when starting another application", async () => {
    mockedSubmitPitch.mockResolvedValue({
      status: "success",
      person_id: "person-1",
      opportunity_id: "opportunity-1",
    });

    render(<PitchSubmissionPage />);
    fireEvent.input(screen.getByPlaceholderText("Your full name"), { target: { value: "Alice Example" } });
    fireEvent.input(screen.getByPlaceholderText("you@company.com"), { target: { value: "alice@example.com" } });
    fireEvent.input(screen.getByPlaceholderText("Your company or project"), { target: { value: "Example AI" } });
    chooseDeck();
    fireEvent.submit(screen.getByRole("button", { name: "Submit application" }).closest("form")!);

    fireEvent.click(await screen.findByRole("button", { name: "Submit Another" }));
    expect(screen.getByPlaceholderText("Your full name")).toHaveValue("");
    expect(screen.getByPlaceholderText("you@company.com")).toHaveValue("");
    expect(screen.getByPlaceholderText("Your company or project")).toHaveValue("");
    expect(screen.getByText("Upload Pitch Deck")).toBeInTheDocument();
    const input = document.querySelector('input[type="file"]');
    expect(input).toHaveProperty("files");
    expect((input as HTMLInputElement).files).toHaveLength(0);
  });
});
