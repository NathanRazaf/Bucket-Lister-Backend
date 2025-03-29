from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_SCHEMA = "bucket_list_app"

# Create database URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create SQLAlchemy engine with explicit schema reference in connect_args
engine = create_engine(
    DATABASE_URL,
    connect_args={"options": f"-csearch_path={DB_SCHEMA}"},
    pool_pre_ping=True  # Helps detect stale connections
)

# Add event listener to set schema for all connections
@event.listens_for(engine, "connect", insert=True)
def set_search_path(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET search_path TO {DB_SCHEMA}")
    dbapi_connection.commit()
    cursor.close()

# Session setup
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        db.execute(f"SET search_path TO {DB_SCHEMA}")
        yield db
    finally:
        db.close()