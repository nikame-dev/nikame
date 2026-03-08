from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime
from sqlalchemy.sql import func
from app.database import Base

class Template(Base):
    __tablename__ = "templates"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    tags = Column(JSON)
    stars = Column(Integer, default=0)
    downloads = Column(Integer, default=0)
    author = Column(String, index=True)
    verified = Column(Boolean, default=False)
    version = Column(String, default="1.0")
    raw_config = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
