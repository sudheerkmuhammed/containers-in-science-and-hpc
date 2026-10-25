from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import os
import socket
import time

app = FastAPI(
    title="HPC & Cloud Container Demo API",
    description="Production-grade API demonstrating container lifecycle, health checks, and signals.",
    version="1.0.0"
)

START_TIME = time.time()

class SystemInfo(BaseModel):
    hostname: str
    uptime_seconds: float
    environment: str
    process_id: int

@app.get("/", tags=["General"])
def read_root():
    return {
        "message": "Containers in Science & HPC Demo API",
        "author": "Sudheer K. Mohammed",
        "docs_url": "/docs"
    }

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
def health_check():
    """
    Health check endpoint utilized by Docker and orchestrators
    to monitor service readiness and liveness.
    """
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "uptime": round(time.time() - START_TIME, 2)
    }

@app.get("/info", response_model=SystemInfo, tags=["Diagnostics"])
def get_system_info():
    """
    Returns runtime process information revealing container isolation details.
    """
    return SystemInfo(
        hostname=socket.gethostname(),
        uptime_seconds=round(time.time() - START_TIME, 2),
        environment=os.getenv("ENVIRONMENT", "development"),
        process_id=os.getpid()
    )
