import { render, screen } from "@testing-library/react";
import { Target } from "lucide-react";
import { describe, expect, test } from "vitest";
import { KeyMetricCard } from "./KeyMetricCard";

describe("KeyMetricCard", () => {
  test("presents the main value and an accessible visual ratio", () => {
    render(<KeyMetricCard icon={Target} label="Thesis aligned" value={6} detail="Strong strategic fit" progress={75} progressLabel="6 of 8 profiles" tone="green" />);

    expect(screen.getByText("6")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Thesis aligned: 6 of 8 profiles" })).toHaveAttribute("aria-valuenow", "75");
  });

  test("keeps an unmeasured metric pending instead of rendering zero", () => {
    render(<KeyMetricCard icon={Target} label="Evidence coverage" value={null} suffix="%" detail="Breadth is not measured" progress={null} progressLabel="0 evidence records" tone="blue" />);

    expect(screen.getByText("Not scored")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Evidence coverage: pending" })).not.toHaveAttribute("aria-valuenow");
  });
});
