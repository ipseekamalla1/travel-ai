import type { components, operations, paths } from "./openapi";

export type { components, operations, paths };

/** Shorthand for a named API schema, e.g. `ApiSchema<"LivenessResponse">`. */
export type ApiSchema<Name extends keyof components["schemas"]> = components["schemas"][Name];
