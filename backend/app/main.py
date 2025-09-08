from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .core.config import settings
from .core.security import verify_token
from .api.v1 import auth, connections, jobs, analytics, superset, settings as app_settings
from .webhooks import superset_webhooks as webhooks

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(connections.router, prefix="/api/v1/connections", tags=["connections"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(superset.router, prefix="/api/v1/superset", tags=["superset"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(app_settings.router, prefix="/api/v1/settings", tags=["settings"])

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION
    }