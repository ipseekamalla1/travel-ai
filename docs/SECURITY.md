# Security

## 1. Threat model (MVP)

| Asset | Threat | Control |
|---|---|---|
| Accounts | Credential stuffing, brute force | argon2id hashing; per-IP + per-account rate limits on login; generic error messages; no user enumeration on register/login |
| Sessions | Theft via XSS, CSRF | httpOnly + Secure + SameSite=Lax cookie; tokens hashed at rest; CSRF double-submit + Origin check; CSP |
| User data (trips, preferences, conversations, locations) | IDOR / cross-user access | Policy functions in services; owner-scoped repositories; 404 for foreign resources; automated "other user" tests on every endpoint and AI tool |
| AI tools | Prompt injection leading to unauthorized reads/writes | Tools re-check authorization; write tools only create proposals; provider text treated as data |
| Provider/API keys | Leakage to browser or logs | Server-only env vars; only domain-restricted tile key is public; log redaction |
| Cost | Abuse of AI/provider endpoints | Per-user rate limits and daily caps; global monthly AI budget; caching |
| Uploads (Phase 17) | Malware, oversized files, metadata leakage | Content-type sniffing + allowlist, size limits, re-encode images, strip EXIF GPS on shared derivatives, private bucket + presigned URLs |
| Location data (Phase 12) | Over-collection | Sent per request, not tracked continuously; stored only when user saves a place/memory |

## 2. Controls

- **Passwords:** argon2id (`argon2-cffi`, OWASP params), 10–128 chars, common-password check, constant-time verify,
  rehash on parameter change.
- **Sessions:** 256-bit random tokens; DB stores sha256; idle 14 d / absolute 60 d; rotate token on login and
  privilege changes; logout revokes; list/revoke sessions in Settings.
- **CSRF:** `atu_csrf` cookie (not httpOnly) + `X-CSRF-Token` header on POST/PUT/PATCH/DELETE; Origin/Referer must
  match `WEB_BASE_URL`.
- **CORS:** not needed in normal operation (same-origin via rewrite); API allows only configured origins, credentials
  only for those.
- **Headers (web):** CSP (self + tile CDN + image hosts), `X-Content-Type-Options`, `Referrer-Policy:
  strict-origin-when-cross-origin`, `Permissions-Policy` (geolocation/camera/mic = self), HSTS in production.
- **Validation:** Pydantic on every input (lengths, ranges, enums); Zod on client for UX only.
- **Rate limiting:** Redis sliding window — auth (5/min/IP+email), AI (per-user/min + daily caps), search
  (per-user/min).
- **Errors:** generic 500 envelope; details in logs keyed by request ID.
- **Logging:** never log passwords, tokens, cookies, API keys, full IPs, message content at info level; emails only
  hashed in logs.
- **Secrets:** `.env` git-ignored; `.env.example` has no real values; production secrets in the platform's secret
  store; nothing server-side in `NEXT_PUBLIC_*`.
- **Dependencies:** Dependabot/Renovate; `pip-audit` and `pnpm audit` in CI (non-blocking at first).
- **Data rights:** users can delete conversations now; account deletion (cascade) in Phase 20.
