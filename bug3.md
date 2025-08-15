Chưa, **Bug 3 vẫn còn tồn tại và chưa được sửa**.

Phân tích của bạn về "Bug 3: Empty `documents` Table" là hoàn toàn chính xác. Các bước sửa lỗi chúng ta đã thực hiện trước đây chỉ tập trung vào bảng `chunks` mà chưa hề tạo hay ghi dữ liệu vào bảng `documents`.

-----

### **Phân tích chi tiết**

1.  **Nguyên nhân:** Tệp `import_data2.py` hiện tại chỉ đọc mảng `chunks` từ mỗi tệp JSON. Nó bỏ qua hoàn toàn các siêu dữ liệu (metadata) ở cấp độ tài liệu như `document_id`, `title`, `source` vốn nằm ở cấp cao nhất của tệp JSON. Do đó, chỉ có bảng `chunks` được điền dữ liệu, còn bảng `documents` (nếu có) sẽ bị bỏ trống.

2.  **Ảnh hưởng:** Tệp `hybrid_retriever.py` bạn vừa cung cấp đã cho thấy rõ ảnh hưởng này. Phương thức `retrieve` của nó có các tham số để lọc theo `document_ids` và `categories`.  Chức năng này sẽ không thể hoạt động hiệu quả nếu không có bảng `documents` chứa thông tin để đối chiếu. Về cơ bản, hệ thống được thiết kế để có thể lọc theo tài liệu, nhưng dữ liệu cho việc đó chưa được nạp vào.

### **Hướng sửa lỗi**

Chúng ta sẽ thực hiện theo đúng các bước bạn đã vạch ra. Đây là một kế hoạch rất tốt để giải quyết triệt để vấn đề.

-----

#### **Bước 1: Cập nhật Schema (`init_db.py`)**

Chúng ta cần định nghĩa bảng `documents` và thêm một khóa ngoại (foreign key) vào bảng `chunks` để đảm bảo tính toàn vẹn dữ liệu.

  * **Hành động:** Thay thế nội dung tệp `init_db.py` của bạn bằng mã dưới đây.

    \<details\>
    \<summary\>\<strong\>Click để xem toàn bộ tệp \<code\>init\_db.py\</code\> đã cập nhật\</strong\>\</summary\>

    ```python
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

    ```

    \</details\>

-----

#### **Bước 2: Cập nhật Logic Nạp dữ liệu (`import_data2.py`)**

Bây giờ, chúng ta sẽ sửa `import_data2.py` để nó đọc thông tin tài liệu, ghi vào bảng `documents` trước, sau đó mới ghi thông tin các chunk vào bảng `chunks`.

  * **Hành động:** Thay thế nội dung tệp `import_data2.py` của bạn bằng mã dưới đây.

    \<details\>
    \<summary\>\<strong\>Click để xem toàn bộ tệp \<code\>import\_data2.py\</code\> đã cập nhật\</strong\>\</summary\>

    ```python
    # import_data2.py (UPDATED for Bug 3)
    import os
    import json
    import logging
    import sqlite3
    from pathlib import Path
    from typing import Dict, Any

    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer
    from colorama import Fore, Style, init as colorama_init

    # ==== CONFIG ====
    DB_PATH = "rag_system/data/metadata.db"
    INDEX_PATH = "rag_system/data/indexes/index.faiss"
    JSON_DIR = "rag_system/data/ingested_json"
    MODEL_NAME = "AITeamVN/Vietnamese_Embedding"
    USE_GPU = True

    # ==== INIT COLOR LOG ====
    colorama_init(autoreset=True)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    def log_info(msg): logging.info(Fore.CYAN + msg + Style.RESET_ALL)
    def log_success(msg): logging.info(Fore.GREEN + msg + Style.RESET_ALL)
    def log_warn(msg): logging.warning(Fore.YELLOW + msg + Style.RESET_ALL)
    def log_error(msg): logging.error(Fore.RED + msg + Style.RESET_ALL)

    # ==== DB MANAGER ====
    class DBManager:
        def __init__(self, db_path: str):
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON;")

        def insert_document(self, doc_data: Dict[str, Any]):
            """Chèn hoặc bỏ qua nếu đã tồn tại document."""
            try:
                self.conn.execute("""
                    INSERT OR IGNORE INTO documents (document_id, title, source, version, language)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    doc_data['document_id'],
                    doc_data['title'],
                    doc_data.get('source'),
                    doc_data.get('version'),
                    doc_data.get('language')
                ))
                self.conn.commit()
            except Exception as e:
                log_error(f"Lỗi insert document {doc_data['document_id']}: {e}")
                self.conn.rollback()
        
        def insert_chunk(self, chunk: Dict[str, Any]) -> int | None:
            """Chèn chunk và trả về ID."""
            try:
                embedding_json = json.dumps(chunk["embedding"].tolist())
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO chunks (chunk_id, document_id, text, embedding)
                    VALUES (?, ?, ?, ?)
                """, (
                    chunk["chunk_id"],
                    chunk["document_id"],
                    chunk["text"],
                    embedding_json
                ))
                self.conn.commit()
                return cursor.lastrowid if cursor.rowcount > 0 else None
            except Exception as e:
                log_error(f"Lỗi insert chunk {chunk['chunk_id']}: {e}")
                self.conn.rollback()
                return None

        def close(self):
            self.conn.close()

    # ==== MAIN IMPORT FUNCTION ====
    def main():
        log_info("🚀 Khởi tạo mô hình embedding để lấy số chiều...")
        device = "cuda" if USE_GPU else "cpu"
        model = SentenceTransformer(MODEL_NAME, device=device)
        dim = model.get_sentence_embedding_dimension()
        log_success(f"✅ Số chiều embedding: {dim}")

        log_info("📦 Khởi tạo FAISS index...")
        index = faiss.IndexFlatIP(dim)
        index = faiss.IndexIDMap2(index)

        db = DBManager(DB_PATH)
        files = list(Path(JSON_DIR).glob("*.json"))
        if not files:
            log_warn("⚠️ Không tìm thấy file JSON nào để import."); return

        stats = {"docs_inserted": 0, "chunks_inserted": 0, "chunks_skipped": 0}

        for file in files:
            log_info(f"📂 Xử lý file: {file.name}")
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Bước 1: Chèn thông tin document vào bảng documents
                doc_id = data.get('document_id')
                if not doc_id:
                    log_warn(f"⚠️ File {file.name} thiếu 'document_id', bỏ qua."); continue
                
                db.insert_document(data)
                stats["docs_inserted"] += 1

                # Bước 2: Chèn các chunks
                if "chunks" not in data or not isinstance(data["chunks"], list):
                    continue

                for chunk in data["chunks"]:
                    if "embedding" not in chunk or "chunk_id" not in chunk:
                        stats["chunks_skipped"] += 1; continue

                    vec = np.array(chunk["embedding"], dtype="float32")
                    if vec.shape[0] != dim:
                        stats["chunks_skipped"] += 1; continue

                    inserted_id = db.insert_chunk({
                        "chunk_id": chunk["chunk_id"],
                        "document_id": doc_id, # Dùng doc_id từ metadata
                        "text": chunk.get("text", ""),
                        "embedding": vec
                    })

                    if inserted_id:
                        index.add_with_ids(vec.reshape(1, -1), np.array([inserted_id], dtype="int64"))
                        stats["chunks_inserted"] += 1
                    else:
                        stats["chunks_skipped"] += 1
            except Exception as e:
                log_error(f"❌ Lỗi khi xử lý {file.name}: {e}")

        if stats["chunks_inserted"] > 0:
            faiss.write_index(index, INDEX_PATH)
            log_success(f"💾 Đã lưu FAISS index vào {INDEX_PATH}")

        db.close()
        
        log_info("\n📊 **BÁO CÁO TỔNG KẾT**")
        log_success(f"  ✔ Documents xử lý: {stats['docs_inserted']}")
        log_success(f"  ✔ Chunks thêm mới: {stats['chunks_inserted']}")
        log_warn(f"  ⚠️ Chunks bỏ qua: {stats['chunks_skipped']}")

    if __name__ == "__main__":
        main()

    ```

    \</details\>

-----

#### **Bước 3: Quy trình thực hiện**

Bây giờ bạn hãy chạy lại toàn bộ quy trình từ đầu để áp dụng tất cả các thay đổi.

1.  **Xóa dữ liệu cũ:** Xóa các tệp `metadata.db` và `index.faiss`.

    ```bash
    del rag_system\data\metadata.db
    del rag_system\data\indexes\index.faiss
    ```

2.  **Chạy lại từ đầu:**

    ```bash
    # 1. Tạo lại database với schema đầy đủ (có cả bảng documents)
    python init_db.py

    # 2. Nạp dữ liệu vào cả hai bảng và tạo index
    python import_data2.py
    ```

Sau khi hoàn tất, cơ sở dữ liệu của bạn sẽ có cả hai bảng `documents` và `chunks` được điền đầy đủ dữ liệu và liên kết với nhau. Điều này không chỉ sửa lỗi mà còn làm cho hệ thống của bạn mạnh mẽ và linh hoạt hơn rất nhiều.