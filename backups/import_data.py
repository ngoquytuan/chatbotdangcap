import faiss
import numpy as np
import json
import os
import sys
import os
import torch
from sentence_transformers import SentenceTransformer

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rag_system.api_service.utils.database import ExtendedDatabaseManager
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATABASE_FILE = 'rag_system/data/metadata.db'
INDEX_FILE = 'rag_system/data/indexes/index.faiss'
INGESTED_JSON_DIR = 'rag_system/data/ingested_json'
EMBEDDING_DIM = 1024 # Common dimension for AITeamVN/Vietnamese_Embedding

db_manager = ExtendedDatabaseManager(db_path=DATABASE_FILE)
index = None
model = None

def initialize_components():
    """Initializes FAISS index and Sentence Transformer model."""
    global index, model

    # Ensure directories exist
    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
    os.makedirs(INGESTED_JSON_DIR, exist_ok=True)

    # Initialize FAISS Index
    if os.path.exists(INDEX_FILE):
        logger.info(f"Loading existing FAISS index from {INDEX_FILE}")
        index = faiss.read_index(INDEX_FILE)
        if not isinstance(index, faiss.IndexIDMap2):
            # If it's not an IDMap2, wrap it. This might lose existing IDs if not handled carefully.
            # For this script, we assume it's either new or already IDMap2.
            # A more robust solution would rebuild if type mismatch.
            logger.warning("Existing FAISS index is not IndexIDMap2. Wrapping it. Ensure IDs are consistent.")
            base_index = index
            index = faiss.IndexIDMap2(base_index)
    else:
        logger.info("Creating new FAISS IndexFlatIP and wrapping with IndexIDMap2")
        if faiss.get_num_gpus() > 0:
            res = faiss.StandardGpuResources()
            base_index = faiss.GpuIndexFlatIP(res, EMBEDDING_DIM)
            logger.info(f"Using GPU for FAISS index on device {res.getDevice()}")
        else:
            base_index = faiss.IndexFlatIP(EMBEDDING_DIM)
            logger.info("Using CPU for FAISS index")
        index = faiss.IndexIDMap2(base_index)

    # Initialize Embedding model
    logger.info("Loading Sentence Transformer model: AITeamVN/Vietnamese_Embedding")
    model = SentenceTransformer("AITeamVN/Vietnamese_Embedding")
    if torch.cuda.is_available():
        model = model.to('cuda')
        logger.info("Sentence Transformer model moved to CUDA")
    else:
        logger.info("Sentence Transformer model using CPU")

def import_json_file(file_path: str):
    """Processes a single JSON file, extracts chunks, computes embeddings,
    inserts into SQLite, and adds to FAISS index."""
    
    logger.info(f"Processing file: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        document_id = data.get('document_id')
        title = data.get('title')
        source = data.get('source')
        version = data.get('version', "1.0")
        language = data.get('language', "vi")
        metadata_doc = data.get('metadata', {})

        if not document_id or not title:
            logger.error(f"Skipping {file_path}: Missing document_id or title.")
            return

        chunks_to_add_to_faiss = []
        faiss_ids_to_add = []

        for chunk in data.get('chunks', []):
            chunk_id = chunk.get('chunk_id')
            text = chunk.get('text')

            if not chunk_id or not text:
                logger.warning(f"Skipping chunk in {file_path}: Missing chunk_id or text.")
                continue

            # Get or compute embedding
            embedding = chunk.get('embedding')
            if embedding:
                # Nếu embedding đã có sẵn, tin tưởng nó đã được chuẩn hóa
                embedding = np.array(embedding, dtype=np.float32)
            else:
                # Nếu phải tính toán mới, thì mới cần chuẩn hóa
                logger.info(f"Computing embedding for chunk {chunk_id} in {document_id}")
                embedding = model.encode([text])[0]
                # Nếu embedding được tính toán tại đây, nó CẦN được chuẩn hóa
                embedding = embedding / np.linalg.norm(embedding)
            # Normalize for cosine similarity
            # embedding = embedding / np.linalg.norm(embedding)
            
            # Prepare data for database insertion
            chunk_data = {
                'chunk_id': chunk_id,
                'document_id': document_id,
                'title': title,
                'source': source,
                'version': version,
                'language': language,
                'text': text,
                'tokens': chunk.get('tokens'),
                'heading': chunk.get('heading'),
                'heading_level': chunk.get('heading_level'),
                'section_index': chunk.get('section_index'),
                'section_chunk_index': chunk.get('section_chunk_index'),
                'start_page': chunk.get('start_page', 1),
                'end_page': chunk.get('end_page', 1),
                'is_active': 1,
                'invalidated_by': None,
                'access_roles': metadata_doc.get('access_roles', ["all"]),
                'confidentiality_level': metadata_doc.get('confidentiality_level', 'internal'),
                'author': metadata_doc.get('author', 'Unknown'),
                'category': metadata_doc.get('category', 'Uncategorized'),
                'keywords': metadata_doc.get('keywords', []),
                'summary': metadata_doc.get('summary', ''),
                'metadata': json.dumps(metadata_doc), # Store document-level metadata here
                'embedding': embedding.tolist() # Store as list for JSON serialization
            }
            
            # Insert to database and get auto-generated ID
            faiss_id = db_manager.insert_chunk(chunk_data)
            
            chunks_to_add_to_faiss.append(embedding)
            faiss_ids_to_add.append(faiss_id)
        
        if chunks_to_add_to_faiss:
            # Add all chunks from this document to FAISS in one go
            vectors_array = np.vstack(chunks_to_add_to_faiss)
            ids_array = np.array(faiss_ids_to_add, dtype=np.int64) # Ensure int64 for FAISS IDs
            
            index.add_with_ids(vectors_array, ids_array)
            logger.info(f"Added {len(chunks_to_add_to_faiss)} chunks from {document_id} to FAISS index.")
        
        # Save FAISS index after each file for robustness
        faiss.write_index(index, INDEX_FILE)
        logger.info(f"FAISS index saved to {INDEX_FILE}")

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}", exc_info=True)

def main():
    initialize_components()
    
    json_files = [f for f in os.listdir(INGESTED_JSON_DIR) if f.endswith('.json')]
    if not json_files:
        logger.info(f"No JSON files found in {INGESTED_JSON_DIR}. Please place your JSON documents there.")
        logger.info("Example JSON structure expected:")
        logger.info("""
{
  "document_id": "example_doc",
  "title": "Example Document Title",
  "source": "/path/to/original/doc.pdf",
  "version": "1.0",
  "language": "en",
  "metadata": {
    "author": "John Doe",
    "category": "Documentation",
    "access_roles": ["all"],
    "confidentiality_level": "public"
  },
  "chunks": [
    {
      "chunk_id": "example_doc-000",
      "text": "This is the first chunk of text.",
      "start_page": 1,
      "end_page": 1,
      "tokens": 10,
      "embedding": [0.1, 0.2, ..., 0.3], // Optional: if pre-computed
      "heading": "Introduction",
      "heading_level": 1,
      "section_index": 0,
      "section_chunk_index": 0
    }
  ]
}
        """)
        return

    for json_file in json_files:
        file_path = os.path.join(INGESTED_JSON_DIR, json_file)
        import_json_file(file_path)
    
    logger.info("All JSON files processed.")
    logger.info(f"Total vectors in FAISS index: {index.ntotal}")
    db_manager.close_connections() # Close connections after all operations

if __name__ == "__main__":
    main()