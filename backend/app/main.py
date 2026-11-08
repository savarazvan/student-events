from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.core.database import get_db, engine, Base

app = FastAPI(title="UBB Student Events API")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1/admin")

@app.on_event("startup")
async def startup_event():
    # Creează automat tabelele definite în modele la pornirea aplicației
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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