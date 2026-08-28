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
from app.api.endpoints.mock_retriever import router as mock_router
from app.api.endpoints.chat import router as chat_router

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
    title="UTH Admission Chatbot API",
    description=(
        "API chatbot tư vấn tuyển sinh UTH. "
        "Hỗ trợ câu hỏi tạo sinh (Gemini), trích dẫn nguồn, phát hiện ngoài phạm vi. "
        "Retrieval: BM25 + Dense (FAISS) Hybrid Weighted 0.4/0.6. "
        "Filters: year_filter + oos_filter (Hướng C). "
        "Post-generation: Attribution Gate (chunk_id check)."
    ),
    version="2.0.0",
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
app.include_router(mock_router, prefix="/api/v1/mock", tags=["mock-retrieval"])
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])


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
