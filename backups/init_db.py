# init_db.py (FINAL, FULL SCHEMA)
import sqlite3
import os

DATABASE_FILE = 'rag_system/data/metadata.db'
DATA_DIR = 'rag_system/data'

PRAGMA_FOREIGN_KEYS = "PRAGMA foreign_keys = ON;"

# Bảng documents để giải quyết Bug 3
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

# Bảng chunks với đầy đủ các cột từ schema gốc của bạn
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
    heading TEXT,
    heading_level INTEGER DEFAULT 1,
    section_index INTEGER DEFAULT 0,
    section_chunk_index INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    invalidated_by TEXT DEFAULT NULL,
    access_roles TEXT DEFAULT '["all"]',
    confidentiality_level TEXT DEFAULT 'internal',
    author TEXT DEFAULT 'Unknown',
    category TEXT DEFAULT 'Uncategorized',
    keywords TEXT DEFAULT '[]',
    summary TEXT DEFAULT '',
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

# Đầy đủ các index mà database.py yêu cầu
CREATE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_chunks_active ON chunks(is_active);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_id ON chunks(chunk_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_version ON chunks(version);
CREATE INDEX IF NOT EXISTS idx_chunks_updated ON chunks(updated_at);
"""
# SQLite không hỗ trợ index trên cột access_roles kiểu TEXT một cách hiệu quả,
# nhưng chúng ta vẫn tạo nó nếu code của bạn yêu cầu.
# Nếu có lỗi về index này, bạn có thể cân nhắc bỏ dòng CREATE INDEX cho access_roles.

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
        print(f"Database '{DATABASE_FILE}' initialized with final, fully compatible schema.")
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    initialize_database()