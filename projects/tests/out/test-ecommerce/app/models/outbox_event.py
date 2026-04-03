from sqlalchemy import Column, String, JSON, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.base_class import Base
import uuid

class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    topic = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    processed = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
