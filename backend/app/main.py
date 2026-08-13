"""
main.py — FastAPI application entry point cho Retrieval API

Usage:
    uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.index_store import index_store
from app.api.endpoints.retrieve import router as retrieve_router

logger = logging.getLogger("main")


# ---------------------------------------------------------------------------
# Lifespan: load index một lần khi startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load FAISS + BM25 index và embedding model khi app khởi động."""
    logger.info("🚀 Khởi động Retrieval API — đang load index...")
    index_store.load()
    logger.info("✅ Index loaded. API sẵn sàng.")
    yield
    logger.info("🛑 Shutting down Retrieval API.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="UTH Admission Chatbot — Retrieval API",
    description=(
        "Retrieval API cho hệ thống chatbot tuyển sinh UTH. "
        "Hỗ trợ BM25, Dense (FAISS) và Hybrid Retrieval (RRF + Weighted Sum). "
        "Lọc theo admission_year và program_type. "
        "Mặc định năm 2026 theo Mục 2.1 đề cương."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — cho phép frontend React (Tuần 6) gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount router
app.include_router(retrieve_router, prefix="/api/v1", tags=["retrieval"])


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------

@app.get("/", tags=["root"])
async def root():
    return {
        "service": "UTH Admission Chatbot — Retrieval API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
