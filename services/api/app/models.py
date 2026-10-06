"""Central import point so Alembic sees every model's table metadata.

Each domain module adds its models import here when it introduces tables (Phase 2 onward).
"""


def import_all_models() -> None:
    # No domain tables exist yet (Phase 1 only enables extensions).
    return None
