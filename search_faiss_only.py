# search_faiss_only.py
import faiss
import numpy as np
from rag_system.api_service.models.embeddings import get_embedding_model

FAISS_INDEX_PATH = "rag_system/data/indexes/index.faiss"

def main():
    # Load FAISS
    index = faiss.read_index(FAISS_INDEX_PATH)
    print(f"FAISS index loaded with {index.ntotal} vectors.")

    # Load embedding model
    model = get_embedding_model()

    # Nhập câu hỏi
    query = input("Nhập câu hỏi: ").strip()
    q_emb = model.encode([query])[0].astype(np.float32)
    q_emb = q_emb / np.linalg.norm(q_emb)  # normalize

    # Search
    distances, ids = index.search(q_emb.reshape(1, -1), 5)
    print("\n=== FAISS raw results ===")
    for i, (idx, score) in enumerate(zip(ids[0], distances[0]), 1):
        print(f"{i}. FAISS ID: {idx}, Score: {score}")

if __name__ == "__main__":
    main()
