# check_chunks.py
import json
from rag_system.api_service.utils.database import extended_db

def main():
    # Thống kê tổng quan
    stats = extended_db.get_database_stats()
    print("=== Database Stats ===")
    for k, v in stats.items():
        print(f"{k}: {v}")
    print()

    # Lấy toàn bộ chunks (không filter is_active)
    with extended_db.get_cursor() as cursor:
        cursor.execute("SELECT id, chunk_id, document_id, title, is_active, invalidated_by, length(embedding) as emb_len FROM chunks ORDER BY id LIMIT 50")
        rows = cursor.fetchall()

    print(f"=== Chunks in DB (max 50 rows) ===")
    for row in rows:
        print(f"ID={row['id']}, chunk_id={row['chunk_id']}, doc_id={row['document_id']}, "
              f"title={row['title']}, active={row['is_active']}, invalidated_by={row['invalidated_by']}, "
              f"embedding_len={row['emb_len']}")
    
    # Kiểm tra embedding có hợp lệ JSON không
    with extended_db.get_cursor() as cursor:
        cursor.execute("""
            SELECT id, chunk_id, embedding 
            FROM chunks 
            WHERE embedding IS NOT NULL AND embedding != '' 
            LIMIT 5
        """)
        emb_rows = cursor.fetchall()

    print("\n=== Embedding samples ===")
    for row in emb_rows:
        try:
            emb = json.loads(row['embedding'])
            print(f"ID={row['id']}, chunk_id={row['chunk_id']}, emb_dim={len(emb)}")
        except json.JSONDecodeError:
            print(f"ID={row['id']}, chunk_id={row['chunk_id']} → INVALID embedding JSON")

if __name__ == "__main__":
    main()
