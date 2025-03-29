from sqlalchemy import Column, Integer, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class BucketItem(Base):
    __tablename__ = "bucket_item"

    id = Column(Integer, primary_key=True, index=True)
    bucket_list_id = Column(Integer, ForeignKey("bucket_list.id", ondelete="CASCADE"), nullable=False, index=True)
    last_modified_by = Column(Integer)
    date_last_modified = Column(DateTime(timezone=True), onupdate=func.now())
    content = Column(Text, nullable=False)
    is_completed = Column(Boolean, default=False)

    # Relationship with BucketList
    bucket_list = relationship("BucketList", back_populates="items")