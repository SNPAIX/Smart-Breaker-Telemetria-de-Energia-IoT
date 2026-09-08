import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Obtener URL de la base de datos desde entorno o fallback local
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://voltguard_user:supersecretpassword@localhost:5432/voltguard_db",
)


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()