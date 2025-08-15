Collecting workspace informationFiltering to most relevant information
Based on the provided documentation, here's a comprehensive README file for the Vietnamese RAG system with FAISS integration:

```markdown
# Vietnamese RAG System with FAISS Integration

A high-performance Retrieval-Augmented Generation (RAG) system optimized for Vietnamese documents using FAISS for vector similarity search.

## Features

- **Fast Query Processing**: Optimized for 100-1000 A4 Vietnamese documents
- **Metadata Filtering**: Support for access control, soft-deletion, and role-based filtering
- **GPU Acceleration**: CUDA support for faster embedding generation and similarity search
- **Hybrid Architecture**: Combines dense vector search (FAISS) with sparse search (BM25)
- **Docker Integration**: Containerized deployment with network isolation
- **Audit Trail**: Comprehensive logging for data changes and operations

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI       │    │   Ollama/LLM    │
│   (LAN Client)  │◄──►│   API Service   │◄──►│   Container     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Data Volume   │
                       │                 │
                       │ ┌─────────────┐ │
                       │ │ FAISS Index │ │
                       │ │ (Vector DB) │ │
                       │ └─────────────┘ │
                       │ ┌─────────────┐ │
                       │ │ SQLite DB   │ │
                       │ │ (Metadata)  │ │
                       │ └─────────────┘ │
                       │ ┌─────────────┐ │
                       │ │ BM25 Index  │ │
                       │ │(Text Search)│ │
                       │ └─────────────┘ │
                       └─────────────────┘
```

## Setup Instructions

### 1. Environment Setup

```bash
# Check CUDA availability
python checkcuda.py

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Project Structure

```
rag_system/
├── api_service/
│   ├── retrieval/
│   │   ├── faiss_retriever.py
│   │   ├── bm25_retriever.py
│   │   └── hybrid_retriever.py
│   ├── models/
│   └── utils/
├── data/
│   ├── raw_documents/
│   ├── ingested_json/
│   └── indexes/
└── main.py
```

### 3. Database Initialization

```bash
# Initialize database schema
python init_db.py

# Verify database structure
python inspect_db.py
```

### 4. Data Ingestion

1. Place documents in raw_documents
2. Process documents into JSON format:
```bash
python ingestionBetter.py
```
3. Import data into database and FAISS index:
```bash
python scripts/import_data2.py
```

### 5. Testing

```bash
# Test FAISS search directly
python search_faiss_only.py

# Test hybrid retriever
python search_test.py

# Verify embeddings
python verify_embeddings.py
```

## Configuration

### Database Schema

```sql
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,       -- FAISS ID
    chunk_id TEXT UNIQUE NOT NULL,              -- "doc-000"
    document_id TEXT NOT NULL,                  -- "doc"
    title TEXT,                                 -- Document title
    text TEXT NOT NULL,                         -- Chunk content
    embedding TEXT,                            -- JSON array of floats
    is_active INTEGER DEFAULT 1,               -- Soft delete flag
    access_roles TEXT DEFAULT '["all"]',       -- JSON array
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### FAISS Configuration

```python
# Index initialization
index = faiss.IndexFlatIP(1024)  # Inner product for cosine similarity
index = faiss.IndexIDMap2(index)  # Custom ID mapping

# GPU acceleration
if faiss.get_num_gpus() > 0:
    res = faiss.StandardGpuResources()
    index = faiss.GpuIndexFlatIP(res, 1024)
```

## Usage Examples

### Document Search

```python
from rag_system.retrieval.hybrid_retriever import HybridRetriever

# Initialize retriever
retriever = HybridRetriever(
    db_path="rag_system/data/metadata.db",
    faiss_path="rag_system/data/indexes/index.faiss",
    model_name="AITeamVN/Vietnamese_Embedding"
)

# Search with filtering
results = retriever.search(
    query="Lý Thái Tổ trị vì",
    user_roles=["admin"],
    desired_k=5
)
```

### Soft Delete Operation

```python
def soft_delete_chunk(chunk_id, reason=""):
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE chunks 
        SET is_active = 0, 
            updated_at = CURRENT_TIMESTAMP
        WHERE chunk_id = ?
    """, (chunk_id,))
    conn.commit()
```

## Maintenance

### Index Rebuild

```bash
# Rebuild FAISS index from database
python scripts/rebuild_index.py

# Monitor dead vector ratio
python check_chunks.py
```

### Performance Monitoring

- **Query Latency**: Target <100ms for search operations
- **Memory Usage**: Monitor RAM/VRAM consumption
- **Index Size**: Track vector count vs active chunks
- **Filter Effectiveness**: Monitor compensation factor hit rate

### Scheduled Tasks

| Frequency | Task |
|-----------|------|
| Daily | Monitor query performance metrics |
| Weekly | Check soft-delete ratio, adjust compensation factor |
| Monthly | Rebuild FAISS index if dead vector ratio > 20% |
| Quarterly | Full database optimization and backup |

## Troubleshooting

### Common Issues

1. **FAISS ID Mismatch**: Ensure SQLite auto-increment IDs match FAISS IDs
2. **Embedding Format**: Store embeddings as JSON arrays in database
3. **Soft Delete Accumulation**: Rebuild index when dead vector ratio exceeds 20%
4. **Memory Issues**: Reduce batch size or use GPU for large datasets

### Debug Scripts

- search_faiss_only.py: Test FAISS search without database
- inspect_db.py: Verify database structure and content
- verify_embeddings.py: Check embedding format and dimensions

## API Endpoints

### Search Endpoint
```http
POST /search
Content-Type: application/json

{
  "query": "Lịch sử Việt Nam",
  "user_roles": ["user"],
  "k": 5
}
```

### Document Management
```http
POST /documents/{doc_id}/soft-delete
{
  "reason": "Outdated content"
}
```

## Scaling Considerations

- **Current Capacity**: ~10-50k chunks (1000 documents)
- **Memory Estimate**: 75MB for 50k 384-dim vectors
- **Scale-up Triggers**: Query latency >100ms consistently
- **Migration Path**: IndexFlatIP → IndexHNSWFlat for >100k vectors

## License

This project is part of a Vietnamese RAG system implementation for internal use.

## Support

For technical support, refer to the documentation in tkclaude.md or check the troubleshooting section.
```

This README provides a comprehensive overview of the Vietnamese RAG system with FAISS integration, covering setup, architecture, usage, and maintenance. It includes practical examples and troubleshooting guidance to help users implement and maintain the system effectively.This README provides a comprehensive overview of the Vietnamese RAG system with FAISS integration, covering setup, architecture, usage, and maintenance. It includes practical examples and troubleshooting guidance to help users implement and maintain the system effectively.