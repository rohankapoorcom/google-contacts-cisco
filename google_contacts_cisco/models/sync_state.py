"""Sync state model."""
import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, String, DateTime
from sqlalchemy.types import Uuid
from sqlalchemy import Enum as SQLEnum
from . import Base


class SyncStatus(str, Enum):
    """Sync status enumeration."""
    
    IDLE = "idle"
    SYNCING = "syncing"
    ERROR = "error"


class SyncState(Base):
    """Sync state model."""
    
    __tablename__ = "sync_states"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_token = Column(String, nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    sync_status = Column(
        SQLEnum(SyncStatus, native_enum=False),
        default=SyncStatus.IDLE,
        nullable=False
    )
    error_message = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<SyncState(id={self.id}, status='{self.sync_status}', last_sync='{self.last_sync_at}')>"

