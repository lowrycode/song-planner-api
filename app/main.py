from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from app.exceptions import validation_exception_handler
from app.routers import auth, songs

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
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/hello")
def hello():
    return {"message": "hello world"}


app.include_router(auth.router, prefix="/auth")
app.include_router(songs.router, prefix="/songs")
