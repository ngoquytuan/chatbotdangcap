import faiss
import numpy as np
import json
import logging
import os # Import os module
from typing import List, Dict, Any, Optional
from rag_system.api_service.utils.database import ExtendedDatabaseManager

logger = logging.getLogger(__name__)

class HybridRetriever:
    def __init__(self, embedding_model, db_manager: ExtendedDatabaseManager, faiss_index_path: str = "rag_system/data/indexes/index.faiss"):
        self.embedding_model = embedding_model
        self.db_manager = db_manager
        self.faiss_index_path = faiss_index_path
        self.faiss_index = self._load_or_create_faiss_index()
        logger.info("HybridRetriever initialized.")

    def _load_or_create_faiss_index(self):
        """Loads FAISS index from disk or creates a new one if it doesn't exist."""
        if self.faiss_index_path and os.path.exists(self.faiss_index_path): # Changed faiss.file_exists to os.path.exists
            logger.info(f"Loading FAISS index from {self.faiss_index_path}")
            index = faiss.read_index(self.faiss_index_path)
            if not isinstance(index, faiss.IndexIDMap2):
                # If it's not an IDMap2, wrap it. This might happen if the index was saved without IDs.
                # For existing indices, this might require a rebuild if IDs are crucial.
                logger.warning("Loaded FAISS index is not IndexIDMap2. Wrapping it. Consider rebuilding if IDs are inconsistent.")
                base_index = index
                index = faiss.IndexIDMap2(base_index)
            logger.info(f"FAISS index loaded with {index.ntotal} vectors.")
            return index
        else:
            logger.warning(f"FAISS index not found at {self.faiss_index_path}. Creating a new IndexFlatIP.")
            # Determine embedding dimension from the model
            dimension = self.embedding_model.get_sentence_embedding_dimension()
            if dimension is None:
                raise ValueError("Could not determine embedding dimension from the model. Cannot create FAISS index.")
            
            base_index = faiss.IndexFlatIP(dimension)
            index = faiss.IndexIDMap2(base_index)
            logger.info(f"New FAISS IndexFlatIP (dim={dimension}) with IndexIDMap2 created.")
            return index

    def retrieve(self, query_text: str, desired_k: int = 5, user_roles: Optional[List[str]] = None, 
                 document_ids: Optional[List[str]] = None, categories: Optional[List[str]] = None,
                 compensation_factor: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves relevant chunks using FAISS and applies metadata filtering.
        """
        if self.faiss_index.ntotal == 0:
            logger.warning("FAISS index is empty. No retrieval possible.")
            return []

        # Compute query embedding
        query_embedding = self.embedding_model.encode([query_text])[0]
        query_embedding = query_embedding / np.linalg.norm(query_embedding) # Normalize for cosine similarity

        # Initial search with compensation factor
        initial_k = desired_k * compensation_factor
        distances, faiss_ids = self.faiss_index.search(
            query_embedding.reshape(1, -1), 
            initial_k
        )
        
        # Filter valid IDs (FAISS returns -1 for empty slots if ntotal < k)
        valid_faiss_ids = [int(id) for id in faiss_ids[0] if id != -1]
        
        if not valid_faiss_ids:
            logger.info("No valid FAISS IDs found after initial search.")
            return []
        
        # Query metadata from SQLite
        # Use the advanced query builder from DatabaseManager
        filtered_chunks = self.db_manager.query_builder.search_chunks_advanced(
            chunk_ids=valid_faiss_ids,
            user_roles=user_roles,
            document_ids=document_ids,
            categories=categories,
            limit=desired_k * compensation_factor # Apply limit after filtering
        )

        # Maintain FAISS ranking order and apply final desired_k
        id_to_metadata = {chunk['id']: chunk for chunk in filtered_chunks}
        ranked_results = []
        
        for i, faiss_id in enumerate(faiss_ids[0]):
            if faiss_id in id_to_metadata:
                chunk_data = id_to_metadata[faiss_id]
                result = {
                    'chunk_id': chunk_data['chunk_id'],
                    'document_id': chunk_data['document_id'],
                    'title': chunk_data['title'],
                    'text': chunk_data['text'],
                    'similarity_score': float(distances[0][i]),
                    'rank': len(ranked_results) + 1,
                    'metadata': json.loads(chunk_data['metadata']) if chunk_data['metadata'] else {}
                }
                ranked_results.append(result)
                
                if len(ranked_results) >= desired_k:
                    break
        
        logger.info(f"Retrieved {len(ranked_results)} results for query '{query_text}'")
        return ranked_results

    def update_faiss_index(self, new_index_path: str):
        """Updates the FAISS index reference after a rebuild."""
        if faiss.file_exists(new_index_path):
            self.faiss_index = faiss.read_index(new_index_path)
            logger.info(f"FAISS index updated to {new_index_path} with {self.faiss_index.ntotal} vectors.")
        else:
            logger.error(f"New FAISS index file not found at {new_index_path}. Index not updated.")
