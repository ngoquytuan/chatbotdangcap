import os
import sys
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging

# Add the parent directory to the sys.path to allow for absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from rag_system.api_service.utils.database import extended_db
from rag_system.api_service.models.embeddings import get_embedding_model
from rag_system.api_service.retrieval.hybrid_retriever import HybridRetriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG System API",
    description="API for Vietnamese RAG System with FAISS and SQLite",
    version="1.0.0"
)

# Placeholder for embedding model and retriever
embedding_model = None
hybrid_retriever = None

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    logger.info("Starting up RAG System API...")
    try:
        # Initialize database connection (already done by extended_db instance)
        db_health = extended_db.health_check()
        if db_health['status'] != 'healthy':
            logger.warning(f"Database health check issues: {db_health['issues']}")
            logger.warning(f"Database health check warnings: {db_health['warnings']}")
        logger.info(f"Database health: {db_health['status']}")

        # Initialize embedding model
        global embedding_model
        embedding_model = get_embedding_model()
        logger.info("Embedding model loaded successfully.")

        # Initialize hybrid retriever
        global hybrid_retriever
        hybrid_retriever = HybridRetriever(embedding_model=embedding_model, db_manager=extended_db)
        logger.info("Hybrid Retriever initialized.")

        logger.info("RAG System API startup complete.")
    except Exception as e:
        logger.error(f"Failed to start up RAG System API: {e}", exc_info=True)
        # Optionally, re-raise or exit if startup failure is critical
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down RAG System API...")
    extended_db.close_connections()
    logger.info("Database connections closed.")
    logger.info("RAG System API shutdown complete.")

@app.get("/health", summary="Health Check", response_model=Dict[str, Any])
async def health_check():
    """
    Performs a health check on the API and its dependencies.
    Returns the status of the database and other components.
    """
    db_status = extended_db.health_check()
    
    model_status = "initialized" if embedding_model else "not_loaded"
    retriever_status = "initialized" if hybrid_retriever else "not_loaded"

    overall_status = "healthy"
    if db_status['status'] in ['error', 'degraded']:
        overall_status = "degraded"
    if model_status == "not_loaded" or retriever_status == "not_loaded":
        overall_status = "degraded"

    return {
        "status": overall_status,
        "database": db_status,
        "embedding_model": model_status,
        "hybrid_retriever": retriever_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    return {"message": "Welcome to the RAG System API. Visit /docs for API documentation."}

# Placeholder for search endpoint
# class SearchRequest(BaseModel):
#     query: str = Field(..., min_length=3, example="Lý Thái Tổ là ai?")
#     top_k: int = Field(5, ge=1, le=20, example=5)
#     user_roles: Optional[List[str]] = Field(None, example=["admin", "user"])
#     document_ids: Optional[List[str]] = Field(None, example=["lythaito", "bienbanbangiao"])
#     categories: Optional[List[str]] = Field(None, example=["history", "legal"])

# @app.post("/search", summary="Search for relevant chunks", response_model=List[Dict[str, Any]])
# async def search_chunks(request: SearchRequest):
#     """
#     Searches the knowledge base for relevant chunks based on the query and filters.
#     """
#     if not hybrid_retriever:
#         raise HTTPException(
#             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
#             detail="Hybrid Retriever is not initialized yet."
#         )
#     
#     try:
#         results = hybrid_retriever.retrieve(
#             query=request.query,
#             top_k=request.top_k,
#             user_roles=request.user_roles,
#             document_ids=request.document_ids,
#             categories=request.categories
#         )
#         return results
#     except Exception as e:
#         logger.error(f"Search failed: {e}", exc_info=True)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"An error occurred during search: {e}"
#         )

# Placeholder for chunk management endpoints
# @app.post("/chunks/soft-delete", summary="Soft-delete a chunk")
# async def soft_delete_chunk_api(chunk_id: str, invalidated_by: Optional[str] = None, reason: Optional[str] = None):
#     if extended_db.soft_delete_chunk(chunk_id, invalidated_by, reason):
#         return {"message": f"Chunk {chunk_id} soft-deleted successfully."}
#     raise HTTPException(status_code=404, detail=f"Chunk {chunk_id} not found.")

# @app.post("/index/rebuild", summary="Trigger FAISS index rebuild")
# async def rebuild_index_api():
#     # This should ideally be an async task or a separate service
#     # For simplicity, we'll call it directly, but be aware of blocking
#     try:
#         # Assuming rebuild_faiss_index is defined elsewhere or in a utility
#         # from rag_system.api_service.utils.indexing import rebuild_faiss_index
#         # rebuild_faiss_index(extended_db, embedding_model) # Needs embedding_model and db
#         return {"message": "FAISS index rebuild initiated. Check logs for progress."}
#     except Exception as e:
#         logger.error(f"Failed to rebuild index: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Failed to rebuild index: {e}")