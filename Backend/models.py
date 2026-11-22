
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from Backend.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)

    username = Column(String(20), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)

    gender = Column(String(10), nullable=False)
    age = Column(Integer, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    test_results = relationship(
        "TestResult",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    test_code = Column(String(50), nullable=False, index=True)

    score = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)

    completed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )

    metrics = Column(JSON, nullable=False, default=dict)
    raw_data = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)

    user = relationship(
        "User",
        back_populates="test_results",
    )
