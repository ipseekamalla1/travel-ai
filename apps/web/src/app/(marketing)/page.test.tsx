import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LIFECYCLE } from "@/features/marketing/lifecycle";

import LandingPage from "./page";

describe("LandingPage", () => {
  it("has a single top-level heading", () => {
    render(<LandingPage />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("lists every lifecycle stage in order", () => {
    render(<LandingPage />);

    const list = screen.getByRole("heading", {
      name: "One trip feeds the next",
    }).nextElementSibling;
    const stages = within(list as HTMLElement).getAllByRole("heading", { level: 3 });
    expect(stages.map((s) => s.textContent)).toEqual(LIFECYCLE.map((s) => s.name));
  });

  it("only links to pages that exist", () => {
    render(<LandingPage />);

    const hrefs = screen.getAllByRole("link").map((link) => link.getAttribute("href"));
    expect(hrefs).toEqual(["/how-it-works"]);
  });
});
