# init_db.py (UPDATED for Bug 3)
import sqlite3
import os

DATABASE_FILE = 'rag_system/data/metadata.db'
DATA_DIR = 'rag_system/data'

# Bật hỗ trợ khóa ngoại
PRAGMA_FOREIGN_KEYS = "PRAGMA foreign_keys = ON;"

# Schema cho bảng documents
CREATE_DOCUMENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT,
    version TEXT,
    language TEXT,
    author TEXT,
    category TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

# Cập nhật bảng chunks với khóa ngoại
CREATE_CHUNKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id TEXT UNIQUE NOT NULL,
    document_id TEXT NOT NULL,
    text TEXT NOT NULL,
    embedding TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents (document_id) ON DELETE CASCADE
);
"""
# Xóa các cột không dùng đến trong chunks để đơn giản hóa
# Các cột metadata chi tiết hơn có thể lấy từ bảng documents

CREATE_AUDIT_LOG_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    old_values TEXT,
    new_values TEXT,
    user_id TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    reason TEXT
);
"""

CREATE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_documents_title ON documents(title);
"""

def initialize_database():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute(PRAGMA_FOREIGN_KEYS)
        cursor.execute(CREATE_DOCUMENTS_TABLE_SQL)
        cursor.execute(CREATE_CHUNKS_TABLE_SQL)
        cursor.execute(CREATE_AUDIT_LOG_TABLE_SQL)
        cursor.executescript(CREATE_INDEXES_SQL)

        conn.commit()
        print(f"Database '{DATABASE_FILE}' initialized successfully with documents and chunks tables.")
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    initialize_database()