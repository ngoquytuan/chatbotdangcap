# D:\Projects\undertest\docsearch\rag_system\api_service\main.py
import os
import sys
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

# Thêm import cho CORS
from fastapi.middleware.cors import CORSMiddleware
# Add the project root to the sys.path to allow for absolute imports
# This helps Python find your modules correctly when running with uvicorn
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
# Import the extended_db and other necessary modules
from rag_system.api_service.utils.database import extended_db
from rag_system.api_service.models.embeddings import get_embedding_model
from rag_system.api_service.retrieval.hybrid_retriever import HybridRetriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# FIX: Khởi tạo FastAPI app
# FIX: Thêm title, description, version cho app
app = FastAPI(
    title="RAG System API",
    description="API for Vietnamese RAG System with FAISS and SQLite",
    version="1.0.0"
)
# FIX: Thêm middleware cho CORS
origins = [
    "*",  # Cho phép tất cả các nguồn. Trong sản phẩm thực tế, bạn nên giới hạn lại.
]
# FIX: Thêm middleware CORS để hỗ trợ các yêu cầu từ frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Global variables for model and retriever
embedding_model = None
hybrid_retriever = None

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    logger.info("Starting up RAG System API...")
    try:
        global embedding_model, hybrid_retriever
        
        db_health = extended_db.health_check()
        if db_health.get('status') != 'healthy':
            logger.warning(f"Database health check warnings: {db_health.get('warnings')}")
        logger.info(f"Database health: {db_health.get('status')}")

        embedding_model = get_embedding_model()
        logger.info("Embedding model loaded successfully.")

        hybrid_retriever = HybridRetriever(embedding_model=embedding_model, db_manager=extended_db)
        logger.info("Hybrid Retriever initialized.")
        logger.info("RAG System API startup complete.")
    except Exception as e:
        logger.error(f"Failed to start up RAG System API: {e}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down RAG System API...")
    extended_db.close_connections()
    logger.info("Database connections closed.")

@app.get("/health", summary="Health Check", response_model=Dict[str, Any])
async def health_check():
    """Performs a health check on the API and its dependencies."""
    db_status = extended_db.health_check()
    model_status = "initialized" if embedding_model else "not_loaded"
    retriever_status = "initialized" if hybrid_retriever else "not_loaded"
    
    status = "healthy"
    if db_status.get('status') != 'healthy' or not model_status or not retriever_status:
        status = "degraded"

    return {
        "status": status,
        "database": db_status,
        "embedding_model": model_status,
        "hybrid_retriever": retriever_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    return {"message": "Welcome to the RAG System API. Visit /docs for API documentation."}

# FIX: Bỏ comment và sửa lỗi tham số cho endpoint /search
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, example="Lý Thái Tổ là ai?")
    top_k: int = Field(5, ge=1, le=20, example=5)
    user_roles: Optional[List[str]] = Field(None, example=["admin", "user"])
    document_ids: Optional[List[str]] = Field(None, example=["lythaito", "bienbanbangiao"])
    categories: Optional[List[str]] = Field(None, example=["Lịch sử", "Pháp lý"])

@app.post("/search", summary="Search for relevant chunks", response_model=List[Dict[str, Any]])
async def search_chunks(request: SearchRequest):
    """
    Searches the knowledge base for relevant chunks based on the query and filters.
    """
    if not hybrid_retriever:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hybrid Retriever is not initialized yet."
        )
    
    try:
        # FIX: Sửa tên tham số cho khớp với định nghĩa hàm retrieve
        # query -> query_text
        # top_k -> desired_k
        results = hybrid_retriever.retrieve(
            query_text=request.query,
            desired_k=request.top_k,
            user_roles=request.user_roles,
            document_ids=request.document_ids,
            categories=request.categories
        )
        return results
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during search: {str(e)}"
        )

# Bạn có thể bỏ comment các endpoint khác khi cần dùng đến
# @app.post("/chunks/soft-delete", ...)
# ...