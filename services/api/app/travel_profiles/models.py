import uuid
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TravelProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Core, typed travel traits the planner reads directly (docs/DATABASE.md, Phase 3)."""

    __tablename__ = "travel_profiles"
    __table_args__ = (
        CheckConstraint("pace IN ('relaxed', 'balanced', 'packed')", name="pace_valid"),
        CheckConstraint(
            "budget_style IN ('shoestring', 'moderate', 'comfortable', 'luxury')",
            name="budget_style_valid",
        ),
        CheckConstraint(
            "accommodation_style IS NULL OR accommodation_style IN "
            "('hostel', 'budget_hotel', 'boutique', 'luxury', 'apartment')",
            name="accommodation_style_valid",
        ),
        CheckConstraint(
            "walking_tolerance IN ('low', 'medium', 'high')", name="walking_tolerance_valid"
        ),
        CheckConstraint("cardinality(travel_styles) <= 5", name="travel_styles_max"),
        CheckConstraint("day_end > day_start", name="day_window_valid"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    travel_styles: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default=text("'{}'::text[]")
    )
    pace: Mapped[str] = mapped_column(Text, server_default="balanced")
    budget_style: Mapped[str] = mapped_column(Text, server_default="moderate")
    accommodation_style: Mapped[str | None] = mapped_column(Text)
    walking_tolerance: Mapped[str] = mapped_column(Text, server_default="medium")
    dietary: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'::text[]"))
    day_start: Mapped[time] = mapped_column(Time, server_default=text("'09:00'"))
    day_end: Mapped[time] = mapped_column(Time, server_default=text("'21:00'"))
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TravelPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A weighted like/dislike for a registry key (ADR-009). Weight -1 (avoid) .. 1 (love)."""

    __tablename__ = "travel_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "key"),
        CheckConstraint("weight BETWEEN -1 AND 1", name="weight_range"),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="confidence_range"),
        CheckConstraint(
            "source IN ('onboarding', 'explicit', 'inferred', 'trip_request')", name="source_valid"
        ),
    )

    # Indexed by the (user_id, key) unique constraint.
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(Text)
    weight: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    source: Mapped[str] = mapped_column(Text)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), server_default=text("1"))
