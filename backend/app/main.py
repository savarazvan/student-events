import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.communication import router as communication_router
from app.api.v1.events import router as events_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.me import router as me_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.tickets import router as tickets_router
from app.core.database import get_db
from app.core.migrations import run_migrations_async
from app.services.scheduler import jobs_enabled, run_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Bring the database schema up to date (Alembic) before serving requests.
    await run_migrations_async()
    stop = asyncio.Event()
    scheduler = asyncio.create_task(run_scheduler(stop)) if jobs_enabled() else None
    yield
    if scheduler is not None:
        stop.set()
        await scheduler


app = FastAPI(
    title="UBB Student Events API",
    lifespan=lifespan,
)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1/admin")
app.include_router(events_router, prefix="/api/v1")
app.include_router(me_router, prefix="/api/v1")
app.include_router(organizations_router, prefix="/api/v1")
app.include_router(communication_router, prefix="/api/v1")
app.include_router(feedback_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(tickets_router, prefix="/api/v1")
@app.get("/")
def read_root():
    return {"message": "API UBB Student Events este online!"}

# Ruta de test pentru conexiunea la PostgreSQL
@app.get("/health/db")
async def check_db_health(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(text("SELECT 1"))
        val = result.scalar()
        return {
            "status": "healthy",
            "database": "PostgreSQL Connected",
            "test_query_result": val
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Eroare la conectarea cu baza de date: {str(e)}"
        )