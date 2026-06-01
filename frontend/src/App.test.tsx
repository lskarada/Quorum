import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("renders the home hero at /", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );
    // The TopBar also renders a "Quorum" brand mark, so target the hero
    // heading specifically rather than any text match.
    expect(
      screen.getByRole("heading", { level: 1, name: /Quorum/i }),
    ).toBeInTheDocument();
  });

  it("renders the diagnose page at /diagnose", () => {
    render(
      <MemoryRouter initialEntries={["/diagnose"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Case presentation/i)).toBeInTheDocument();
  });
});
