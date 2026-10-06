"""Redis fixed-window rate limiting (docs/SECURITY.md §2)."""

import hashlib
import ipaddress
import time

from fastapi import Request
from redis.asyncio import Redis

from app.core.errors import RateLimitedError


class RateLimiter:
    def __init__(self, redis: Redis, *, prefix: str = "rl") -> None:
        self._redis = redis
        self._prefix = prefix

    async def hit(self, bucket: str, identity: str, *, limit: int, window_s: int) -> None:
        """Count one request; raise `RateLimitedError` once `limit` is exceeded in the window.

        Identities are hashed so keys never contain raw emails or IPs.
        """
        window = int(time.time()) // window_s
        digest = hashlib.sha256(identity.encode()).hexdigest()[:32]
        key = f"{self._prefix}:{bucket}:{digest}:{window}"
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, window_s)
            count, _ = await pipe.execute()
        if int(count) > limit:
            retry_after = window_s - int(time.time()) % window_s
            raise RateLimitedError(
                "Too many attempts. Please wait a moment and try again.",
                retry_after_s=retry_after,
            )


def client_ip(request: Request, *, trust_forwarded_for: bool) -> str:
    if trust_forwarded_for:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def ip_prefix(ip: str) -> str | None:
    """Coarsened IP for session metadata (/24 for IPv4, /48 for IPv6) — never the full address."""
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return None
    prefix = 24 if address.version == 4 else 48
    return str(ipaddress.ip_network(f"{address}/{prefix}", strict=False))
