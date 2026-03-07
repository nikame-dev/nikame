from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from app.db.base_class import Base

class DocumentMeta(Base):
    __tablename__ = "document_meta"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    chunk_count = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
