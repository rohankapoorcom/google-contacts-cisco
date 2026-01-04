"""Phone number model."""
import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Index
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from . import Base


class PhoneNumber(Base):
    """Phone number model."""
    
    __tablename__ = "phone_numbers"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id = Column(Uuid(as_uuid=True), ForeignKey("contacts.id"), nullable=False)
    value = Column(String, nullable=False)
    display_value = Column(String, nullable=False)
    type = Column(String, nullable=True)
    primary = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    contact = relationship("Contact", back_populates="phone_numbers")
    
    # Indexes
    __table_args__ = (
        Index('idx_phone_number_value', 'value'),
        Index('idx_phone_number_contact', 'contact_id'),
    )
    
    def __repr__(self):
        return f"<PhoneNumber(id={self.id}, value='{self.value}', type='{self.type}')>"

