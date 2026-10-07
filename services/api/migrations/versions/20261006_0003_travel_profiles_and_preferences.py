"""travel profiles and preferences

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "travel_preferences",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("weight", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "confidence",
            sa.Numeric(precision=4, scale=3),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source IN ('onboarding', 'explicit', 'inferred', 'trip_request')",
            name=op.f("ck_travel_preferences_source_valid"),
        ),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 1", name=op.f("ck_travel_preferences_confidence_range")
        ),
        sa.CheckConstraint(
            "weight BETWEEN -1 AND 1", name=op.f("ck_travel_preferences_weight_range")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_travel_preferences_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_travel_preferences")),
        sa.UniqueConstraint("user_id", "key", name=op.f("uq_travel_preferences_user_id_key")),
    )
    op.create_table(
        "travel_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "travel_styles",
            sa.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("pace", sa.Text(), server_default="balanced", nullable=False),
        sa.Column("budget_style", sa.Text(), server_default="moderate", nullable=False),
        sa.Column("accommodation_style", sa.Text(), nullable=True),
        sa.Column("walking_tolerance", sa.Text(), server_default="medium", nullable=False),
        sa.Column(
            "dietary", sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False
        ),
        sa.Column("day_start", sa.Time(), server_default=sa.text("'09:00'"), nullable=False),
        sa.Column("day_end", sa.Time(), server_default=sa.text("'21:00'"), nullable=False),
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "accommodation_style IS NULL OR accommodation_style IN ('hostel', 'budget_hotel', 'boutique', 'luxury', 'apartment')",
            name=op.f("ck_travel_profiles_accommodation_style_valid"),
        ),
        sa.CheckConstraint(
            "budget_style IN ('shoestring', 'moderate', 'comfortable', 'luxury')",
            name=op.f("ck_travel_profiles_budget_style_valid"),
        ),
        sa.CheckConstraint(
            "pace IN ('relaxed', 'balanced', 'packed')", name=op.f("ck_travel_profiles_pace_valid")
        ),
        sa.CheckConstraint(
            "walking_tolerance IN ('low', 'medium', 'high')",
            name=op.f("ck_travel_profiles_walking_tolerance_valid"),
        ),
        sa.CheckConstraint(
            "cardinality(travel_styles) <= 5", name=op.f("ck_travel_profiles_travel_styles_max")
        ),
        sa.CheckConstraint("day_end > day_start", name=op.f("ck_travel_profiles_day_window_valid")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_travel_profiles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_travel_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_travel_profiles_user_id")),
    )


def downgrade() -> None:
    op.drop_table("travel_profiles")
    op.drop_table("travel_preferences")
