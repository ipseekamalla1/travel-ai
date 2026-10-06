import type { ApiSchema } from "@atu/types";

import { apiFetch } from "@/lib/api/client";

export type User = ApiSchema<"UserOut">;
export type LoginInput = ApiSchema<"LoginRequest">;
export type RegisterInput = ApiSchema<"RegisterRequest">;

export const authApi = {
  me: () => apiFetch<User>("/auth/me"),
  login: (input: LoginInput) => apiFetch<User>("/auth/login", { json: input }),
  register: (input: RegisterInput) => apiFetch<User>("/auth/register", { json: input }),
  logout: () => apiFetch<void>("/auth/logout", { method: "POST" }),
};
