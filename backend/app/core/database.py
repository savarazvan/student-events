import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Preia URL-ul din variabilele de mediu (Docker) sau folosește localhost pentru rulare locală fără Docker
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/student_events_db"
)

# Creează Engine-ul asincron SQLAlchemy
engine = create_async_engine(
    DATABASE_URL, 
    echo=True,       # Afișează query-urile SQL în consolă (util pentru dev)
    future=True
)

# Factory pentru crearea sesiunilor asincrone
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Clasa Base din care vor moșteni toate modelele din app/models/
class Base(DeclarativeBase):
    pass

# Dependency-ul FastAPI injectat în rute pentru sesiunea de DB
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()