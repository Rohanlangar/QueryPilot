"""
QueryPilot — Application Entry Point

FastAPI application configuration, middleware registration,
route mounting, and lifecycle events.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.config import settings
from app.db.database import init_db, close_db, async_session_factory
import app.models  # Ensure all models are registered with Base.metadata
from app.models.rbac import Role
from app.models.user import User
from app.core.security import hash_password
from app.services.connection_manager import connection_manager

# Import API routes
from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.connections import router as connections_router
from app.api.routes.chat import router as chat_router
from app.api.routes.schema import router as schema_router
from app.api.routes.admin import router as admin_router
from app.api.routes.audit import router as audit_router
from app.api.websockets.chat_ws import router as ws_router
from app.api.routes.agent_query import router as agent_query_router
from app.api.middleware.rate_limiter import RateLimiter

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("querypilot")


async def seed_default_roles():
    """Seed default built-in roles and default admin user if they do not exist."""
    default_roles = [
        {
            "name": "admin",
            "description": "Administrator with full system privileges",
            "can_manage_users": True,
            "can_manage_connections": True,
            "can_manage_policies": True,
            "can_view_audit": True,
        },
        {
            "name": "analyst",
            "description": "Data Analyst with broad querying capabilities",
            "can_manage_users": False,
            "can_manage_connections": True,
            "can_manage_policies": False,
            "can_view_audit": False,
        },
        {
            "name": "viewer",
            "description": "Read-only viewer restricted to permitted tables",
            "can_manage_users": False,
            "can_manage_connections": False,
            "can_manage_policies": False,
            "can_view_audit": False,
        },
    ]

    async with async_session_factory() as session:
        try:
            for role_data in default_roles:
                result = await session.execute(
                    select(Role).where(Role.name == role_data["name"])
                )
                existing = result.scalar_one_or_none()
                if not existing:
                    new_role = Role(**role_data)
                    session.add(new_role)

            # Seed default admin user
            admin_res = await session.execute(
                select(User).where(User.username == "admin")
            )
            admin_user = admin_res.scalar_one_or_none()
            if not admin_user:
                new_admin = User(
                    email="admin@querypilot.local",
                    username="admin",
                    hashed_password=hash_password("admin123"),
                    full_name="System Administrator",
                    role="admin",
                )
                session.add(new_admin)
                logger.info("Default admin user created (admin / admin123).")

            await session.commit()
            logger.info("Default roles and users initialized.")
        except Exception as e:
            await session.rollback()
            logger.warning(f"Role/User initialization skipped or failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and graceful shutdown."""
    logger.info("Starting QueryPilot Backend...")
    # Initialize database tables
    await init_db()
    # Seed default roles
    await seed_default_roles()
    logger.info("Database schema initialized and ready.")

    yield

    # Shutdown
    logger.info("Shutting down QueryPilot Backend...")
    await connection_manager.close_all()
    await close_db()
    logger.info("Cleanup completed. Goodbye!")


# Create FastAPI application
app = FastAPI(
    title="QueryPilot",
    description="Autonomous SQL Database Analyst — Backend API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────
# CORS Middleware
origins = settings.cors_origins or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if "*" not in origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory Rate Limiting Middleware
app.add_middleware(RateLimiter, requests_per_minute=120)


# ── Global Exception Handlers ────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Fallback handler for unhandled exceptions."""
    logger.exception(f"Unhandled error handling {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred. Please check server logs.",
            "path": request.url.path,
        },
    )


# ── Route Registration ────────────────────────────────────────
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(connections_router)
app.include_router(chat_router)
app.include_router(schema_router)
app.include_router(admin_router)
app.include_router(audit_router)
app.include_router(ws_router)
app.include_router(agent_query_router)
