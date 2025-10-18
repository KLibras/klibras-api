from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import user, recognition
from app.db.database_connection import engine, Base, AsyncSessionLocal
from app.db.initial_data import create_initial_data 
from app.core.config import settings
from app.db.models.processing_job import ProcessingJob
import logging

app = FastAPI(title="KLibras API", version="1.0.0")

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Event handler que carrega a aplicação na inicialização"""
    logger.info("Starting application, creating database tables if needed")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(ProcessingJob.metadata.create_all)
    logger.info("Database tables created successfully")

    logger.info("Checking and populating initial data...")
    async with AsyncSessionLocal() as session:
        await create_initial_data(session)

app.include_router(user.router)
logger.info("User router included")

app.include_router(recognition.router)
logger.info("Recognition router included")

@app.get("/health")
async def health_check():
    return {"status": "ok"}