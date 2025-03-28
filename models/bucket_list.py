from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class BucketList(Base):
    __tablename__ = "bucket_list"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    created_by = Column(Integer, nullable=False)
    date_created = Column(DateTime(timezone=True), server_default=func.now())
    is_private = Column(Boolean, default=True)
    share_token = Column(String(64), unique=True)

    # Relationship with BucketItem
    items = relationship("BucketItem", back_populates="bucket_list", cascade="all, delete-orphan")


class BucketItem(Base):
    __tablename__ = "bucket_items"

    id = Column(Integer, primary_key=True, index=True)
    bucket_list_id = Column(Integer, ForeignKey("bucket_list.id", ondelete="CASCADE"), nullable=False)
    last_modified_by = Column(Integer)
    date_last_modified = Column(DateTime(timezone=True), onupdate=func.now())
    content = Column(Text)
    is_completed = Column(Boolean, default=False)

    # Relationship with BucketList
    bucket_list = relationship("BucketList", back_populates="items")