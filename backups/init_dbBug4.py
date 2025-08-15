# init_db.py (FINAL VERSION, fixes schema mismatch)
import sqlite3
import os

DATABASE_FILE = 'rag_system/data/metadata.db'
DATA_DIR = 'rag_system/data'

PRAGMA_FOREIGN_KEYS = "PRAGMA foreign_keys = ON;"

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

# Khôi phục lại tất cả các cột gốc để tương thích với database.py
CREATE_CHUNKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id TEXT UNIQUE NOT NULL,
    document_id TEXT NOT NULL,
    title TEXT,
    source TEXT,
    version TEXT DEFAULT "1.0",
    language TEXT DEFAULT "vi",
    text TEXT NOT NULL,
    tokens INTEGER,
    is_active INTEGER DEFAULT 1,
    metadata TEXT,
    embedding TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents (document_id) ON DELETE CASCADE
);
"""

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

# Khôi phục lại các index gốc
CREATE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_chunks_active ON chunks(is_active);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_id ON chunks(chunk_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_version ON chunks(version);
CREATE INDEX IF NOT EXISTS idx_chunks_updated ON chunks(updated_at);
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
        print(f"Database '{DATABASE_FILE}' initialized with full compatible schema.")
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    initialize_database()