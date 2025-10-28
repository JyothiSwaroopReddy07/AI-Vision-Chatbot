"""Main FastAPI application"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import async_engine
from app.core.redis_client import redis_client
from app.api import auth, chat, upload, pathway, pubmed, user, bookmarks, starred, msigdb


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown"""
    # Startup
    print("Starting up...")
    # Connect to Redis
    await redis_client.connect()
    
    yield
    
    # Shutdown
    print("Shutting down...")
    # Disconnect from Redis
    await redis_client.disconnect()
    # Dispose database engine
    await async_engine.dispose()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Chatbot Agent for Vision Domain Research",
    lifespan=lifespan
)

# Configure CORS - Allow localhost origins with credentials
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(user.router, prefix="/api/v1/user", tags=["User"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["Upload"])
app.include_router(pathway.router, prefix="/api/v1/pathway", tags=["Pathway"])
app.include_router(pubmed.router, prefix="/api/v1/pubmed", tags=["PubMed"])
app.include_router(msigdb.router, prefix="/api/v1/msigdb", tags=["MSigDB"])
app.include_router(bookmarks.router, prefix="/api/v1/bookmarks", tags=["Bookmarks"])
app.include_router(starred.router, prefix="/api/v1/starred", tags=["Starred"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z"
    }


@app.get("/test-db")
async def test_db():
    """Test database connection"""
    from app.core.database import get_db
    from app.models.user import User
    from sqlalchemy import select
    
    async for db in get_db():
        try:
            result = await db.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            return {"status": "database_connected", "user_count": 1 if user else 0}
        except Exception as e:
            return {"status": "database_error", "error": str(e)}
        break

