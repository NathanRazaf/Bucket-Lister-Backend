from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class BucketList(Base):
    __tablename__ = "bucket_list"
    __table_args__ = {"schema": "bucket_list_app"}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    created_by = Column(Integer, nullable=False, index=True)
    date_created = Column(DateTime(timezone=True), server_default=func.now())
    is_private = Column(Boolean, default=True)
    share_token = Column(String(64), unique=True)

    # Relationship with BucketItem
    items = relationship("BucketItem", back_populates="bucket_list", cascade="all, delete-orphan")
