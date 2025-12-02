# backend/app/database/session.py
from sqlmodel import create_engine, Session, SQLModel
from pathlib import Path
import os

DB_URL = os.getenv("DATABASE_URL", "sqlite:///./dev_agentic.db")
engine = create_engine(DB_URL, echo=False)

def init_db():
    from backend.app.database import models  # noqa: F401
    SQLModel.metadata.create_all(engine)

def get_session() -> Session:
    return Session(engine)