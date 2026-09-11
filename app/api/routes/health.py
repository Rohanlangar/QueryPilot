"""
QueryPilot — Health Check Routes
"""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "QueryPilot",
        "version": "0.1.0",
    }


@router.get("/")
async def root():
    """Root endpoint — API info."""
    return {
        "name": "QueryPilot",
        "description": "Autonomous SQL Database Analyst — Backend API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
