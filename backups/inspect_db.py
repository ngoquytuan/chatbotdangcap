# inspect_db.py
import json
from rag_system.api_service.utils.database import extended_db

def main():
    # Lấy kết nối DB từ ExtendedDatabaseManager
    conn = extended_db.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, chunk_id, document_id, title, is_active, invalidated_by, 
               LENGTH(embedding) as embedding_len, metadata
        FROM chunks
        ORDER BY id ASC
    """)
    rows = cursor.fetchall()

    print(f"Tổng số chunks trong DB: {len(rows)}\n")
    for row in rows:
        chunk_id = row[1]
        doc_id = row[2]
        title = row[3]
        is_active = row[4]
        invalidated_by = row[5]
        embedding_len = row[6]
        metadata = row[7]

        print(f"ID: {row[0]} | chunk_id: {chunk_id} | doc_id: {doc_id}")
        print(f"  Title: {title}")
        print(f"  is_active: {is_active} | invalidated_by: {invalidated_by}")
        print(f"  embedding length: {embedding_len}")
        print(f"  metadata: {metadata}")
        print("-" * 60)

    conn.close()

if __name__ == "__main__":
    main()
