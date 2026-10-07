"use client";

import { useId } from "react";

import { cn } from "@/lib/utils";

export type Choice = { value: string; label: string; description?: string };

type BaseProps = {
  legend: string;
  hint?: string;
  choices: readonly Choice[];
  layout?: "cards" | "chips";
  className?: string;
};

type SingleProps = BaseProps & {
  multiple?: false;
  value: string | null;
  onChange: (value: string) => void;
};

type MultiProps = BaseProps & {
  multiple: true;
  value: readonly string[];
  onChange: (value: string[]) => void;
  max?: number;
};

/**
 * Accessible single (radio) or multiple (checkbox) choice group, rendered as cards or chips.
 * Native inputs keep keyboard and screen-reader behaviour standard.
 */
export function ChoiceGroup(props: SingleProps | MultiProps) {
  const { legend, hint, choices, layout = "cards", className } = props;
  const name = useId();
  const hintId = hint ? `${name}-hint` : undefined;
  const selected = (value: string) =>
    props.multiple ? props.value.includes(value) : props.value === value;
  const atMax = props.multiple && props.max !== undefined && props.value.length >= props.max;

  const toggle = (value: string) => {
    if (!props.multiple) return props.onChange(value);
    props.onChange(
      props.value.includes(value)
        ? props.value.filter((v) => v !== value)
        : [...props.value, value],
    );
  };

  return (
    <fieldset className={cn("grid gap-3", className)} aria-describedby={hintId}>
      <legend className="mb-1 text-lg font-semibold">{legend}</legend>
      {hint ? (
        <p id={hintId} className="-mt-2 text-sm text-muted-foreground">
          {hint}
        </p>
      ) : null}
      <div className={layout === "cards" ? "grid gap-2 sm:grid-cols-2" : "flex flex-wrap gap-2"}>
        {choices.map((choice) => {
          const id = `${name}-${choice.value}`;
          const checked = selected(choice.value);
          return (
            <div key={choice.value}>
              <input
                id={id}
                type={props.multiple ? "checkbox" : "radio"}
                name={name}
                value={choice.value}
                checked={checked}
                disabled={!checked && atMax}
                onChange={() => toggle(choice.value)}
                className="peer sr-only"
              />
              <label
                htmlFor={id}
                className={cn(
                  "block cursor-pointer border transition-colors select-none",
                  "peer-focus-visible:ring-3 peer-focus-visible:ring-ring/50",
                  "peer-checked:border-primary peer-checked:bg-accent peer-checked:text-accent-foreground",
                  "peer-disabled:cursor-not-allowed peer-disabled:opacity-50",
                  layout === "cards"
                    ? "h-full rounded-xl bg-card p-4 hover:border-primary/50"
                    : "rounded-full bg-card px-4 py-2 text-sm hover:border-primary/50",
                )}
              >
                <span className="font-medium">{choice.label}</span>
                {layout === "cards" && choice.description ? (
                  <span className="mt-1 block text-sm text-muted-foreground">
                    {choice.description}
                  </span>
                ) : null}
              </label>
            </div>
          );
        })}
      </div>
    </fieldset>
  );
}
