import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { ChoiceGroup } from "./choice-group";

const CHOICES = [
  { value: "food", label: "Food-first" },
  { value: "culture", label: "Culture" },
  { value: "nature", label: "Nature" },
];

function Multi({ max }: { max?: number }) {
  const [value, setValue] = useState<string[]>([]);
  return (
    <ChoiceGroup
      multiple
      legend="Style"
      choices={CHOICES}
      value={value}
      onChange={setValue}
      max={max}
    />
  );
}

function Single() {
  const [value, setValue] = useState<string | null>(null);
  return <ChoiceGroup legend="Pace" choices={CHOICES} value={value} onChange={setValue} />;
}

describe("ChoiceGroup", () => {
  it("is a labelled group of checkboxes when multiple", async () => {
    const user = userEvent.setup();
    render(<Multi />);

    await user.click(screen.getByLabelText("Food-first"));
    await user.click(screen.getByLabelText("Nature"));

    expect(screen.getByRole("group", { name: "Style" })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Food-first" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Nature" })).toBeChecked();
    await user.click(screen.getByLabelText("Nature"));
    expect(screen.getByRole("checkbox", { name: "Nature" })).not.toBeChecked();
  });

  it("disables unselected options once the maximum is reached", async () => {
    const user = userEvent.setup();
    render(<Multi max={2} />);

    await user.click(screen.getByLabelText("Food-first"));
    await user.click(screen.getByLabelText("Culture"));

    expect(screen.getByRole("checkbox", { name: "Nature" })).toBeDisabled();
    expect(screen.getByRole("checkbox", { name: "Culture" })).toBeEnabled();
  });

  it("behaves as a radio group when single", async () => {
    const user = userEvent.setup();
    render(<Single />);

    await user.click(screen.getByLabelText("Culture"));
    await user.click(screen.getByLabelText("Nature"));

    expect(screen.getByRole("radio", { name: "Nature" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Culture" })).not.toBeChecked();
  });
});
