from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 1. The Engine manages the actual TCP connection pool to the database
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg://postgres:Ahsan3439?@localhost/ai_project"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 2. SessionLocal produces temporary workspace connections per request
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session():
    try:
        db=SessionLocal()
        yield db
    finally:
        db.close()