from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# ✅ Use psycopg2 (Standard PostgreSQL Driver)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:%40Honghong0630@db.worxdgbsibuzfvrdxhtk.supabase.co:5432/postgres")

# ✅ Sync Engine
engine = create_engine(DATABASE_URL, echo=True)

# ✅ Session Factory (Synchronous)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ✅ Declarative Base
Base = declarative_base()

# ✅ Dependency for DB Sessions (Sync)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

