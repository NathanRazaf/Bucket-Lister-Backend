from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base


class Account(Base):
    __tablename__ = "account"
    __table_args__ = {"schema": "bucket_list_app"}

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    date_created = Column(DateTime(timezone=True), server_default=func.now())