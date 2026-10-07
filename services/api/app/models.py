"""Central import point so Alembic sees every model's table metadata.

Each domain module adds its models import here when it introduces tables.
"""


def import_all_models() -> None:
    import app.auth.models
    import app.travel_profiles.models
    import app.users.models  # noqa: F401
