# search_test.py
import os
import json
import logging
from rag_system.api_service.utils.database import extended_db
from rag_system.api_service.models.embeddings import get_embedding_model
from rag_system.api_service.retrieval.hybrid_retriever import HybridRetriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # 1. Load embedding model
    logger.info("Loading embedding model...")
    embedding_model = get_embedding_model()
    
    # 2. Init HybridRetriever
    retriever = HybridRetriever(
        embedding_model=embedding_model,
        db_manager=extended_db,
        faiss_index_path="rag_system/data/indexes/index.faiss"
    )
    
    # 3. Nhập câu hỏi
    query = input("Nhập câu hỏi của bạn: ").strip()
    
    # 4. Thực hiện tra cứu
    results = retriever.retrieve(query_text=query, desired_k=5)
    
    # 5. In kết quả
    if results:
        print("\n=== KẾT QUẢ TÌM KIẾM ===")
        for r in results:
            print(f"[{r['rank']}] {r['title']} - {r['chunk_id']}")
            print(f"Score: {r['similarity_score']:.4f}")
            print(f"Text: {r['text']}")
            print(f"Metadata: {json.dumps(r['metadata'], ensure_ascii=False)}\n")
    else:
        print("Không tìm thấy kết quả phù hợp.")

if __name__ == "__main__":
    main()
