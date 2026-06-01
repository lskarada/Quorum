import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VerdictHeader } from "@/components/verdict-header";
import { DifferentialTable } from "@/components/differential-table";
import type { Differential } from "@/lib/types";

const diff: Differential = {
  candidates: [
    { name: "Giant-cell myocarditis", posterior: 0.78, rationale: "r" },
    { name: "Cardiac sarcoidosis", posterior: 0.16, rationale: "r" },
    { name: "Lymphoma", posterior: 0.06, rationale: "r" },
  ],
  iteration: 1,
};

describe("data-verify invariants", () => {
  it("leading diagnosis = rank-1 candidate", () => {
    const { container } = render(
      <VerdictHeader verdict={null} liveDifferential={diff} />,
    );
    expect(
      container
        .querySelector("[data-verify-leading]")
        ?.getAttribute("data-verify-leading"),
    ).toBe("Giant-cell myocarditis");
  });

  it("shown posteriors sum to ~1.0", () => {
    const { container } = render(
      <DifferentialTable verdict={null} liveDifferential={diff} />,
    );
    const sum = Number(
      container
        .querySelector("[data-verify-posterior-sum]")
        ?.getAttribute("data-verify-posterior-sum"),
    );
    expect(sum).toBeGreaterThan(0.99);
    expect(sum).toBeLessThan(1.01);
  });

  it("renders one row per candidate", () => {
    render(<DifferentialTable verdict={null} liveDifferential={diff} />);
    expect(screen.getByText("Giant-cell myocarditis")).toBeInTheDocument();
    expect(screen.getByText("Lymphoma")).toBeInTheDocument();
  });
});
