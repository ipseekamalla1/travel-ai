from datetime import datetime

from sqlalchemy import CHAR, CheckConstraint, DateTime, Text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("char_length(display_name) BETWEEN 1 AND 80", name="display_name_length"),
        CheckConstraint("home_currency ~ '^[A-Z]{3}$'", name="home_currency_iso"),
        CheckConstraint("units IN ('metric', 'imperial')", name="units_valid"),
        CheckConstraint("status IN ('active', 'disabled')", name="status_valid"),
    )

    email: Mapped[str] = mapped_column(CITEXT, unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(Text)
    home_currency: Mapped[str] = mapped_column(CHAR(3), server_default="USD")
    locale: Mapped[str] = mapped_column(Text, server_default="en")
    units: Mapped[str] = mapped_column(Text, server_default="metric")
    status: Mapped[str] = mapped_column(Text, server_default="active")
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def is_active(self) -> bool:
        return self.status == "active"
