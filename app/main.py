import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from app.exceptions import validation_exception_handler
from app.routers import auth, songs, activities, networks, users


def get_allowed_origins() -> list[str]:
    origins = os.getenv("CORS_ALLOW_ORIGINS", "")
    return [origin.strip() for origin in origins.split(",") if origin.strip()]


app = FastAPI(
    title="Task Manager API",
    description="A simple API for managing tasks with token-based authentication",
    version="1.0.0",
)

# Ensure sensitive fields (e.g. password) don't show when invalid Pydantic model input
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["api-root"], summary="(public) API root info")
def root():
    return {
        "message": "Welcome to the Song Analysis API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


app.include_router(activities.router, prefix="/activities")
app.include_router(auth.router, prefix="/auth")
app.include_router(networks.router, prefix="/networks")
app.include_router(songs.router, prefix="/songs")
app.include_router(users.router, prefix="/users")
