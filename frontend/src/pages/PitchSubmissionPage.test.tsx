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
    fireEvent.input(screen.getByPlaceholderText("Founder Name"), { target: { value: "Alice Example" } });
    fireEvent.input(screen.getByPlaceholderText("Email Address"), { target: { value: "alice@example.com" } });
    fireEvent.input(screen.getByPlaceholderText("Company Name"), { target: { value: "Example AI" } });
    chooseDeck();
    fireEvent.submit(screen.getByRole("button", { name: "Submit Pitch" }).closest("form")!);

    expect(await screen.findByText("Pitch Received")).toBeInTheDocument();
    expect(screen.getByTestId("submission-id")).toHaveTextContent("opportunity-1");
  });

  it("keeps the form and displays an error when submission fails", async () => {
    mockedSubmitPitch.mockRejectedValue(new Error("network failure"));

    render(<PitchSubmissionPage />);
    fireEvent.input(screen.getByPlaceholderText("Founder Name"), { target: { value: "Alice Example" } });
    fireEvent.input(screen.getByPlaceholderText("Email Address"), { target: { value: "alice@example.com" } });
    fireEvent.input(screen.getByPlaceholderText("Company Name"), { target: { value: "Example AI" } });
    chooseDeck();
    fireEvent.submit(screen.getByRole("button", { name: "Submit Pitch" }).closest("form")!);

    expect(await screen.findByRole("alert")).toHaveTextContent("could not submit");
    expect(screen.queryByText("Pitch Received")).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByPlaceholderText("Company Name")).toHaveValue("Example AI"));
  });

  it("resets all form fields and the deck when starting another application", async () => {
    mockedSubmitPitch.mockResolvedValue({
      status: "success",
      person_id: "person-1",
      opportunity_id: "opportunity-1",
    });

    render(<PitchSubmissionPage />);
    fireEvent.input(screen.getByPlaceholderText("Founder Name"), { target: { value: "Alice Example" } });
    fireEvent.input(screen.getByPlaceholderText("Email Address"), { target: { value: "alice@example.com" } });
    fireEvent.input(screen.getByPlaceholderText("Company Name"), { target: { value: "Example AI" } });
    chooseDeck();
    fireEvent.submit(screen.getByRole("button", { name: "Submit Pitch" }).closest("form")!);

    fireEvent.click(await screen.findByRole("button", { name: "Submit Another" }));
    expect(screen.getByPlaceholderText("Founder Name")).toHaveValue("");
    expect(screen.getByPlaceholderText("Email Address")).toHaveValue("");
    expect(screen.getByPlaceholderText("Company Name")).toHaveValue("");
    expect(screen.getByText("Upload Pitch Deck")).toBeInTheDocument();
  });
});
