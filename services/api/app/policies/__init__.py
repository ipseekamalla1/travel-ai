"""Authorization policies (docs/ARCHITECTURE.md §5).

Services and AI tools call these instead of comparing IDs inline, so every ownership rule lives in
one place. Resources the user may not see raise `NotFoundError` (404), never 403, so IDs can't be
probed for existence.
"""

import uuid
from typing import Protocol

from app.core.errors import NotFoundError


class UserOwned(Protocol):
    @property
    def user_id(self) -> uuid.UUID: ...


def require_owned[T: UserOwned](resource: T | None, user_id: uuid.UUID, *, name: str) -> T:
    """Return the resource if it exists and belongs to `user_id`; otherwise 404."""
    if resource is None or resource.user_id != user_id:
        raise NotFoundError(f"{name} not found.")
    return resource
