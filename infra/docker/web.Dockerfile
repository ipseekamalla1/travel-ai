# syntax=docker/dockerfile:1.7
# Next.js web app image. Build context: repository root (pnpm workspace).

FROM node:22-alpine AS base
ENV PNPM_HOME=/pnpm \
    PATH="/pnpm:$PATH" \
    COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    NEXT_TELEMETRY_DISABLED=1
RUN npm install -g corepack@latest && corepack enable
WORKDIR /repo

# ---- dependencies (cached on lockfile + manifests) ----
FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/types/package.json packages/types/package.json
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install --frozen-lockfile --filter @atu/web...

# ---- development: source is bind-mounted by compose ----
FROM deps AS dev
COPY apps/web apps/web
COPY packages packages
WORKDIR /repo/apps/web
EXPOSE 3000
CMD ["pnpm", "dev", "--hostname", "0.0.0.0", "--port", "3000"]

# ---- build ----
FROM deps AS build
ARG API_INTERNAL_URL=http://api:8000
ENV API_INTERNAL_URL=${API_INTERNAL_URL}
COPY apps/web apps/web
COPY packages packages
RUN pnpm --filter @atu/web build

# ---- production: standalone server, non-root ----
FROM node:22-alpine AS prod
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
WORKDIR /app
RUN addgroup -S atu && adduser -S atu -G atu
COPY --from=build --chown=atu:atu /repo/apps/web/.next/standalone ./
COPY --from=build --chown=atu:atu /repo/apps/web/.next/static ./apps/web/.next/static
USER atu
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
