"""Sync state model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from . import Base, GUID


class SyncState(Base):
    """Sync state model."""
    
    __tablename__ = "sync_states"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    sync_token = Column(String, nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    sync_status = Column(String, default="idle", nullable=False)
    error_message = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<SyncState(id={self.id}, status='{self.sync_status}', last_sync='{self.last_sync_at}')>"

