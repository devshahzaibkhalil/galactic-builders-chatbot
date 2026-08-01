"""Lead model.

Fields must not be duplicated in any other model. Business rules about when
a lead may be committed live in app/services/lead_service.py, not here.
"""
from __future__ import annotations

import enum
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import Base
from app.security.encryption import get_blind_index_key, get_field_encryption_key


class InterestResponse(str, enum.Enum):
    PENDING = "pending"
    YES = "yes"
    NO = "no"


class LeadStatus(str, enum.Enum):
    DRAFT = "draft"                # in-progress estimate flow
    NOT_CONFIRMED = "not_confirmed"  # customer said No to interest confirmation
    NEW = "new"                    # confirmed + submitted, awaiting triage
    ASSIGNED = "assigned"
    IN_REVIEW = "in_review"
    CLOSED = "closed"


def _new_public_reference() -> str:
    """Non-sequential, non-guessable public lead reference (e.g. GB-7K2N9Q)."""
    return f"GB-{secrets.token_hex(4).upper()[:6]}"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    public_reference: Mapped[str] = mapped_column(String(16), unique=True, index=True, default=_new_public_reference)

    # -- Project details --
    service_key: Mapped[str] = mapped_column(String(64), index=True)
    project_description: Mapped[str] = mapped_column(Text)
    property_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    project_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timeline: Mapped[str | None] = mapped_column(String(32), nullable=True)
    budget_range: Mapped[str | None] = mapped_column(String(32), nullable=True)
    photo_count: Mapped[int] = mapped_column(Integer, default=0)

    # -- Location --
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    street_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    service_area_status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # -- Contact --
    # Stored encrypted at rest (see app/security/encryption.py). Never
    # queried directly — lookups go through the paired blind-index column.
    # Accessed as `lead.email` / `lead.phone` via the properties below, so
    # every existing call site (lead_service, email templates, admin
    # routes, tests) keeps working unchanged.
    email_ciphertext: Mapped[str | None] = mapped_column("email_ciphertext", Text, nullable=True)
    email_blind_index: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    phone_ciphertext: Mapped[str | None] = mapped_column("phone_ciphertext", Text, nullable=True)
    phone_blind_index: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    preferred_contact_method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    best_contact_time: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # -- Interest confirmation (mandatory step before final lead submission) --
    interest_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    interest_response: Mapped[InterestResponse] = mapped_column(
        Enum(InterestResponse, native_enum=False, length=10),
        default=InterestResponse.PENDING,
        nullable=False,
    )
    interest_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    interest_confirmation_version: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # -- Flags / status --
    safety_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, native_enum=False, length=20), default=LeadStatus.DRAFT
    )
    assigned_admin_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    source_page: Mapped[str | None] = mapped_column(String(255), nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # soft delete

    consent: Mapped["LeadConsent | None"] = relationship(
        back_populates="lead", uselist=False, cascade="all, delete-orphan"
    )

    # -- Transparent encryption for email/phone --
    @property
    def email(self) -> str | None:
        if not self.email_ciphertext:
            return None
        from app.services.encryption_service import decrypt_field
        return decrypt_field(self.email_ciphertext, key=get_field_encryption_key())

    @email.setter
    def email(self, value: str | None) -> None:
        from app.services.encryption_service import compute_blind_index, encrypt_field
        if not value:
            self.email_ciphertext = None
            self.email_blind_index = None
            return
        self.email_ciphertext = encrypt_field(value, key=get_field_encryption_key())
        self.email_blind_index = compute_blind_index(value, blind_index_key=get_blind_index_key())

    @property
    def phone(self) -> str | None:
        if not self.phone_ciphertext:
            return None
        from app.services.encryption_service import decrypt_field
        return decrypt_field(self.phone_ciphertext, key=get_field_encryption_key())

    @phone.setter
    def phone(self, value: str | None) -> None:
        from app.services.encryption_service import compute_blind_index, encrypt_field
        if not value:
            self.phone_ciphertext = None
            self.phone_blind_index = None
            return
        self.phone_ciphertext = encrypt_field(value, key=get_field_encryption_key())
        self.phone_blind_index = compute_blind_index(value, blind_index_key=get_blind_index_key())

    @staticmethod
    def email_lookup_index(email: str) -> str:
        """Use this to build a WHERE Lead.email_blind_index == ... query —
        never query email_ciphertext directly, it isn't equality-comparable
        (Fernet ciphertext is non-deterministic)."""
        from app.services.encryption_service import compute_blind_index
        return compute_blind_index(email, blind_index_key=get_blind_index_key())


class LeadConsent(Base):
    """Project-contact consent — deliberately separate from interest confirmation.

    A Yes on interest confirmation is never treated as consent by itself;
    this row must be created independently before a lead can be committed
    as LeadStatus.NEW.
    """
    __tablename__ = "lead_consents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), unique=True)

    contact_consent_given: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    marketing_consent_given: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_text_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lead: Mapped["Lead"] = relationship(back_populates="consent")
