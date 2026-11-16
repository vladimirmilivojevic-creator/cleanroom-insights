"""SQLAlchemy 2.0 models.

Every business table carries ``organization_id``: that is how tenants are separated.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, UTCDateTime, utcnow


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))  # admin | trainer | trainee
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    organization: Mapped[Organization] = relationship(lazy="joined")


class TrainingSession(Base):
    """One run of a VR training module by one trainee."""

    __tablename__ = "training_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    trainee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    module: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="running")  # running | completed
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    score: Mapped[int | None]
    passed: Mapped[bool | None]

    trainee: Mapped[User] = relationship(lazy="joined")


class SessionEvent(Base):
    """A single event sent by the headset: a completed step or a deviation."""

    __tablename__ = "session_events"
    __table_args__ = (Index("ix_session_events_org_kind", "organization_id", "kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id"), index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    kind: Mapped[str] = mapped_column(String(20))  # step | deviation
    step: Mapped[str] = mapped_column(String(50))
    deviation: Mapped[str | None] = mapped_column(String(50))
    severity: Mapped[str | None] = mapped_column(String(10))  # minor | major | critical
    penalty: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Certificate(Base):
    """Issued when a trainee passes a module. Valid for one year (annual requalification)."""

    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)  # public verification code
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    trainee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id"), unique=True)
    module: Mapped[str] = mapped_column(String(50))
    score: Mapped[int]
    issued_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    valid_until: Mapped[datetime] = mapped_column(UTCDateTime)

    trainee: Mapped[User] = relationship(lazy="joined")


class AuditLog(Base):
    """Append-only, hash-chained audit trail (who did what, when).

    Each entry stores the hash of the previous entry of the same organisation,
    so changing or deleting an old row breaks the chain and is detected.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # None = system
    action: Mapped[str] = mapped_column(String(50))
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(50))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))
