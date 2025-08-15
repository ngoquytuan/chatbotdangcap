import sqlite3
import json
import os
from pathlib import Path

def test_bug3_fix():
    """Test if Bug 3 (empty documents table) has been completely fixed."""
    
    # Define paths
    db_path = "rag_system/data/metadata.db"
    json_dir = "rag_system/data/ingested_json"
    
    # Check if database exists
    if not os.path.exists(db_path):
        print("❌ Database file does not exist. Run import_data2.py first.")
        return False
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if documents table exists and has data
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
    if not cursor.fetchone():
        print("❌ 'documents' table does not exist.")
        conn.close()
        return False
    
    cursor.execute("SELECT COUNT(*) FROM documents")
    doc_count = cursor.fetchone()[0]
    
    if doc_count == 0:
        print("❌ 'documents' table is empty.")
        conn.close()
        return False
    
    print(f"✅ 'documents' table exists with {doc_count} records.")
    
    # Check if chunks table exists and has data
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chunks'")
    if not cursor.fetchone():
        print("❌ 'chunks' table does not exist.")
        conn.close()
        return False
    
    cursor.execute("SELECT COUNT(*) FROM chunks")
    chunk_count = cursor.fetchone()[0]
    
    if chunk_count == 0:
        print("❌ 'chunks' table is empty.")
        conn.close()
        return False
    
    print(f"✅ 'chunks' table exists with {chunk_count} records.")
    
    # Check foreign key relationship
    cursor.execute("PRAGMA foreign_key_list(chunks)")
    fk_info = cursor.fetchall()
    
    if not fk_info:
        print("❌ No foreign key constraints found in 'chunks' table.")
        conn.close()
        return False
    
    print("✅ Foreign key constraints exist in 'chunks' table.")
    
    # Verify document-chunk relationship
    cursor.execute("""
        SELECT d.document_id, d.title, COUNT(c.id) as chunk_count
        FROM documents d
        LEFT JOIN chunks c ON d.document_id = c.document_id
        GROUP BY d.document_id, d.title
        ORDER BY chunk_count DESC
    """)
    
    doc_chunk_pairs = cursor.fetchall()
    
    if not doc_chunk_pairs:
        print("❌ No document-chunk relationships found.")
        conn.close()
        return False
    
    print("\n📊 Document-Chunk Relationship Summary:")
    for doc_id, title, chunk_count in doc_chunk_pairs:
        print(f"  - Document: {doc_id} ({title}) has {chunk_count} chunks")
    
    # Check if all JSON files have been processed
    json_files = list(Path(json_dir).glob("*.json"))
    if not json_files:
        print("\n⚠️ No JSON files found in ingestion directory.")
    else:
        print(f"\n📁 Found {len(json_files)} JSON files in ingestion directory.")
        
        # Check if all documents in JSON exist in database
        for json_file in json_files:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            doc_id = data.get('document_id')
            if doc_id:
                cursor.execute("SELECT 1 FROM documents WHERE document_id = ?", (doc_id,))
                if not cursor.fetchone():
                    print(f"❌ Document {doc_id} from {json_file.name} not found in database.")
                else:
                    print(f"✅ Document {doc_id} from {json_file.name} found in database.")
    
    # Close connection
    conn.close()
    
    print("\n🎉 Bug 3 fix verification complete!")
    return True

if __name__ == "__main__":
    test_bug3_fix()