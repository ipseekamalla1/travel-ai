import type { ApiSchema } from "@atu/types";

import type { User } from "@/features/auth/api";
import { apiFetch } from "@/lib/api/client";

export type AccountUpdate = ApiSchema<"UserUpdate">;

export const accountApi = {
  update: (data: AccountUpdate) => apiFetch<User>("/me", { method: "PATCH", json: data }),
};
