"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config.settings import settings
from app.api.v1 import moderate, health
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.cache import CacheMiddleware
from app.utils.redis_client import init_redis_pool, close_redis_pool
from app.utils.colored_logging import ColoredFormatter

# Configure logging with colors
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Apply colored formatter to all handlers
formatter = ColoredFormatter(
    fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

for handler in logging.root.handlers:
    handler.setFormatter(formatter)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("Starting Moderation API...")
    logger.info(f"Environment: {settings.env}")
    logger.info(f"API Version: {settings.api_version}")

    # Initialize Redis connection pool
    init_redis_pool()

    yield

    # Shutdown
    logger.info("Shutting down Moderation API...")
    close_redis_pool()


# Create FastAPI application
app = FastAPI(
    title="Moderation API",
    description="OpenAI-compatible moderation API with batch support, Redis caching, and rate limiting",
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add custom middleware (order matters - last added is executed first)
# So we add in reverse order: logging -> rate limit -> cache
app.add_middleware(CacheMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(LoggingMiddleware)

# Include routers
app.include_router(moderate.router, prefix="/v1", tags=["Moderation"])
app.include_router(health.router, prefix="/v1", tags=["Health"])


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect to docs."""
    return {
        "message": "Moderation API",
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/v1/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.env == "development",
        log_level=settings.log_level.lower(),
    )