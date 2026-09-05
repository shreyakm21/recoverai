from fastapi import FastAPI

from app.api.recovery import router as recovery_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="RecoverAI",
    description="AI-powered payment failure and revenue recovery engine",
    version="0.1.0"
)

"""
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
"""
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recovery_router)


@app.get("/")
def root():
    return {
        "project": "RecoverAI",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }