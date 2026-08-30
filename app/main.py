from fastapi import FastAPI

app = FastAPI(
    title="RecoverAI",
    description="AI-powered payment failure and revenue recovery engine",
    version="0.1.0"
)


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