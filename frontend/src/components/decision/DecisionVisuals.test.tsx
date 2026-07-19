import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { DecisionScoreIndicator, DecisionStatusBadge } from "./DecisionVisuals";

describe("decision visualizations", () => {
  test("exposes score and readiness semantics", () => {
    render(
      <>
        <DecisionScoreIndicator label="Thesis match" value={82} detail="Strategy fit" />
        <DecisionScoreIndicator label="Evidence quality" value={68} detail="Source confidence" />
        <DecisionStatusBadge state="ready" />
      </>,
    );

    expect(screen.getByRole("meter", { name: "Thesis match: 82%" })).toHaveAttribute("aria-valuenow", "82");
    expect(screen.getByRole("meter", { name: "Evidence quality: 68%" })).toHaveAttribute("aria-valuenow", "68");
    expect(screen.getByRole("status", { name: /ready for review/i })).toBeInTheDocument();
  });
});
