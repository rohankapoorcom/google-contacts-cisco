"""Contact model."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.orm import relationship
from . import Base, GUID


class Contact(Base):
    """Contact model."""

    __tablename__ = "contacts"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    resource_name = Column(String, unique=True, nullable=False, index=True)
    etag = Column(String, nullable=True)
    given_name = Column(String, nullable=True)
    family_name = Column(String, nullable=True)
    display_name = Column(String, nullable=False, index=True)
    organization = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    deleted = Column(Boolean, default=False, nullable=False)
    synced_at = Column(DateTime, nullable=True)

    # Relationships
    phone_numbers = relationship(
        "PhoneNumber", back_populates="contact", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_contact_display_name", "display_name"),
        Index("idx_contact_resource_name", "resource_name"),
    )

    def __repr__(self):
        return f"<Contact(id={self.id}, display_name='{self.display_name}')>"
