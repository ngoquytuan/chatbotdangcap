Chưa, **bug 2 này vẫn còn tồn tại trong hệ thống của bạn**.

Các bước sửa lỗi trước đó đã giải quyết thành công **Bug 1** (lỗi `UnicodeDecodeError` do định dạng lưu trữ embedding), nhưng chưa giải quyết vấn đề về sự không khớp ID giữa FAISS và SQLite.

-----

### **Phân tích Bug 2**

  * **Vấn đề cốt lõi:** Script `import_data2.py` hiện tại đang tạo ID cho FAISS bằng cách **băm (hash) giá trị `chunk_id`** (ví dụ: `hash("readme-001")`), tạo ra một con số rất lớn. Trong khi đó, bảng `chunks` trong SQLite có một cột `id` là số nguyên tự tăng (1, 2, 3,...).
  * **Hậu quả:** Khi bạn tìm kiếm trên FAISS, nó trả về các ID dạng hash. Nhưng khi `HybridRetriever` dùng các ID này để truy vấn trong SQLite với điều kiện `WHERE id IN (...)`, nó không tìm thấy kết quả nào vì các ID không khớp nhau.

### **Hướng sửa lỗi (Theo Option 1 được đề xuất)**

Chúng ta sẽ thực hiện theo **Option 1** trong tài liệu của bạn: **sử dụng `id` tự tăng của SQLite làm ID cho FAISS**. Đây là giải pháp đơn giản, hiệu quả và đúng với thiết kế ban đầu.

Dưới đây là các bước chi tiết để sửa lỗi.

-----

#### **Bước 1: Sửa đổi Script Nạp dữ liệu (`import_data2.py`)**

Chúng ta cần thay đổi script để sau khi chèn một chunk vào SQLite, nó sẽ lấy `id` vừa được tạo ra và dùng ID đó để thêm vào FAISS.

  * **Hành động:** Mở tệp `import_data2.py` và áp dụng hai thay đổi sau:

    1.  **Trong lớp `DBManager`, sửa phương thức `insert_chunk`** để nó trả về `id` của hàng vừa được chèn.

        ```python
        # Sửa trong class DBManager
        def insert_chunk(self, chunk: Dict[str, Any]) -> int | None:
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
                # Trả về ID của hàng vừa được chèn
                return cursor.lastrowid if cursor.rowcount > 0 else None
            except Exception as e:
                log_error(f"Lỗi insert chunk {chunk['chunk_id']}: {e}")
                return None
        ```

    2.  **Trong hàm `main`, cập nhật vòng lặp xử lý** để nhận và sử dụng `id` này.

        ```python
        # Sửa trong hàm main()
        # ... (bỏ qua phần đầu)
        for chunk in data["chunks"]:
            # ... (bỏ qua phần kiểm tra dữ liệu)

            vec = np.array(chunk["embedding"], dtype="float32")
            # ... (bỏ qua phần kiểm tra dimension)

            # Thêm chunk vào DB và lấy về ID tự tăng
            inserted_id = db.insert_chunk({
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk.get("document_id", ""),
                "text": chunk.get("text", ""),
                "embedding": vec
            })

            # Nếu chèn thành công và nhận được ID
            if inserted_id is not None:
                # DÙNG ID TỪ SQLITE LÀM ID CHO FAISS
                faiss_id = inserted_id
                index.add_with_ids(vec.reshape(1, -1), np.array([faiss_id], dtype="int64"))
                stats["chunks_inserted"] += 1
            else:
                # Chunk đã tồn tại hoặc có lỗi khi chèn
                stats["chunks_skipped"] += 1
        # ... (phần còn lại của hàm)
        ```

-----

#### **Bước 2: Sửa đổi Script Xây dựng lại Index (`rebuild_index.py`)**

Tương tự, `rebuild_index.py` cũng phải được cập nhật để đọc đúng cột `id` từ database thay vì tự tính toán hash.

  * **Hành động:** Mở tệp `rebuild_index.py` và thay thế nội dung của nó bằng phiên bản đã được sửa đổi dưới đây.

    ```python
    # rebuild_index.py (đã sửa)
    import os
    import sqlite3
    import json
    import logging
    from pathlib import Path

    import faiss
    import numpy as np
    from colorama import Fore, Style, init as colorama_init

    # ==== CONFIG ====
    DB_PATH = "rag_system/data/metadata.db"
    INDEX_PATH = "rag_system/data/indexes/index.faiss"
    EMBEDDING_DIM = 1024

    # ==== INIT COLOR LOG ====
    colorama_init(autoreset=True)
    # ... (giữ nguyên các hàm log)

    def rebuild_faiss_index():
        log_info(f"🔍 Bắt đầu xây dựng lại FAISS index từ '{DB_PATH}'...")
        # ... (giữ nguyên phần kết nối DB)
        
        # Sửa câu lệnh SQL để lấy cả cột 'id'
        cursor.execute("SELECT id, embedding FROM chunks WHERE embedding IS NOT NULL")
        rows = cursor.fetchall()
        # ... (phần còn lại)
        
        for row in rows:
            try:
                embedding_list = json.loads(row['embedding'])
                vector = np.array(embedding_list, dtype="float32")
                
                if vector.shape[0] != EMBEDDING_DIM:
                    continue

                # FIX: Lấy ID trực tiếp từ cột 'id' của database
                faiss_id = row['id']
                vectors.append(vector)
                ids.append(faiss_id)

            except (json.JSONDecodeError, TypeError) as e:
                log_warn(f"⚠️ Lỗi khi xử lý embedding cho chunk có id={row.get('id', 'N/A')}: {e}. Bỏ qua.")
                continue
        # ... (giữ nguyên phần còn lại của script)
    ```

    *Lưu ý: Tôi đã rút gọn mã ở trên để làm nổi bật các thay đổi. Bạn nên thay thế toàn bộ tệp bằng phiên bản đầy đủ chính xác hơn ở cuối câu trả lời này.*

-----

#### **Bước 3: Thực hiện và Kiểm tra**

1.  **Xóa dữ liệu cũ:** Xóa tệp `metadata.db` và `index.faiss` để đảm bảo không còn dữ liệu với ID cũ.
    ```bash
    del rag_system\data\metadata.db
    del rag_system\data\indexes\index.faiss
    ```
2.  **Chạy lại quy trình:**
    ```bash
    # 1. Tạo lại database với schema chuẩn
    python init_db.py

    # 2. Nạp dữ liệu với logic ID đã được sửa
    python import_data2.py
    ```
3.  **Cập nhật Logic Truy vấn:**
    Trong tệp `hybrid_retriever.py`, bạn cần đảm bảo rằng câu lệnh SQL đang truy vấn vào cột `id` chính xác. Nó nên có dạng:
    ```sql
    SELECT * FROM chunks WHERE id IN (?, ?, ...)
    ```
    Vì FAISS ID và `chunks.id` giờ đã đồng bộ, logic này sẽ hoạt động.

-----

Dưới đây là toàn bộ nội dung của hai tệp đã được sửa đổi để bạn tiện sao chép.

\<details\>
\<summary\>\<strong\>Click để xem toàn bộ tệp \<code\>import\_data2.py\</code\> đã sửa\</strong\>\</summary\>

```python
# import_data2.py (FIXED for Bug 2)
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

    def insert_chunk(self, chunk: Dict[str, Any]) -> int | None:
        """
        Chèn một chunk vào DB.
        Trả về ID của hàng được chèn (lastrowid) nếu thành công.
        Trả về None nếu chunk đã tồn tại hoặc có lỗi.
        """
        try:
            # Sửa lỗi Bug 1: Chuyển embedding sang chuỗi JSON
            embedding_json = json.dumps(chunk["embedding"].tolist())
            cursor = self.conn.cursor()
            
            # Sử dụng INSERT OR IGNORE để tránh lỗi nếu chunk_id đã tồn tại
            # Lưu ý: Cột chunk_id trong init_db.py phải là UNIQUE
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

            # Nếu rowcount > 0, nghĩa là đã chèn thành công
            if cursor.rowcount > 0:
                return cursor.lastrowid
            return None # Chunk đã tồn tại, không chèn mới

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
        log_warn("⚠️ Không tìm thấy file JSON nào để import.")
        return

    stats = {"files_ok": 0, "files_err": 0, "chunks_inserted": 0, "chunks_skipped": 0}

    for file in files:
        log_info(f"📂 Xử lý file: {file.name}")
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "chunks" not in data or not isinstance(data["chunks"], list):
                log_warn(f"⚠️ File {file.name} không có trường 'chunks'")
                stats["files_err"] += 1; continue

            for chunk in data["chunks"]:
                if "embedding" not in chunk or "chunk_id" not in chunk:
                    stats["chunks_skipped"] += 1; continue

                vec = np.array(chunk["embedding"], dtype="float32")
                if vec.shape[0] != dim:
                    stats["chunks_skipped"] += 1; continue

                # Thêm chunk vào DB và lấy về ID tự tăng
                inserted_id = db.insert_chunk({
                    "chunk_id": chunk["chunk_id"],
                    "document_id": chunk.get("document_id", ""),
                    "text": chunk.get("text", ""),
                    "embedding": vec
                })

                if inserted_id is not None:
                    # Sửa lỗi Bug 2: Dùng ID từ SQLite làm FAISS ID
                    faiss_id = inserted_id
                    index.add_with_ids(vec.reshape(1, -1), np.array([faiss_id], dtype="int64"))
                    stats["chunks_inserted"] += 1
                else:
                    log_warn(f"⚠️ Chunk {chunk['chunk_id']} đã tồn tại hoặc có lỗi, bỏ qua.")
                    stats["chunks_skipped"] += 1
            stats["files_ok"] += 1
        except Exception as e:
            log_error(f"❌ Lỗi khi xử lý {file.name}: {e}")
            stats["files_err"] += 1

    if stats["chunks_inserted"] > 0:
        os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
        faiss.write_index(index, INDEX_PATH)
        log_success(f"💾 Đã lưu FAISS index vào {INDEX_PATH}")
    else:
        log_warn("⚠️ Không có chunk nào được thêm vào, không tạo file FAISS index.")

    db.close()
    
    log_info("\n📊 **BÁO CÁO TỔNG KẾT**")
    log_success(f"  ✔ Files thành công: {stats['files_ok']}")
    log_error(f"  ✖ Files lỗi: {stats['files_err']}")
    log_success(f"  ✔ Chunks thêm mới: {stats['chunks_inserted']}")
    log_warn(f"  ⚠️ Chunks bỏ qua: {stats['chunks_skipped']}")

if __name__ == "__main__":
    main()
```

\</details\>
\<details\>
\<summary\>\<strong\>Click để xem toàn bộ tệp \<code\>rebuild\_index.py\</code\> đã sửa\</strong\>\</summary\>

```python
# rebuild_index.py (FIXED for Bug 2)
import os
import sqlite3
import json
import logging
from pathlib import Path

import faiss
import numpy as np
from colorama import Fore, Style, init as colorama_init

# ==== CONFIG ====
DB_PATH = "rag_system/data/metadata.db"
INDEX_PATH = "rag_system/data/indexes/index.faiss"
EMBEDDING_DIM = 1024

# ==== INIT COLOR LOG ====
colorama_init(autoreset=True)
logging.basicConfig(level=logging.INFO, format="%(message)s")

def log_info(msg): logging.info(Fore.CYAN + msg + Style.RESET_ALL)
def log_success(msg): logging.info(Fore.GREEN + msg + Style.RESET_ALL)
def log_warn(msg): logging.warning(Fore.YELLOW + msg + Style.RESET_ALL)
def log_error(msg): logging.error(Fore.RED + msg + Style.RESET_ALL)

def rebuild_faiss_index():
    log_info(f"🔍 Bắt đầu xây dựng lại FAISS index từ '{DB_PATH}'...")

    db_file = Path(DB_PATH)
    if not db_file.exists():
        log_error(f"❌ Không tìm thấy file database tại: {DB_PATH}"); return

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Sửa lỗi Bug 2: Lấy cột 'id' để làm FAISS ID
        cursor.execute("SELECT id, embedding FROM chunks WHERE embedding IS NOT NULL")
        rows = cursor.fetchall()
    except Exception as e:
        log_error(f"❌ Lỗi khi đọc dữ liệu từ database: {e}"); return
    finally:
        if 'conn' in locals() and conn: conn.close()

    if not rows:
        log_warn("⚠️ Không có dữ liệu trong database để xây dựng index."); return

    log_info(f"📚 Tìm thấy {len(rows)} chunks trong database.")
    log_info(f"📦 Khởi tạo FAISS index với dimension: {EMBEDDING_DIM}")
    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    index = faiss.IndexIDMap2(index)

    vectors, ids = [], []
    for row in rows:
        try:
            # Sửa lỗi Bug 1: Đọc chuỗi JSON từ DB
            embedding_list = json.loads(row['embedding'])
            vector = np.array(embedding_list, dtype="float32")
            
            if vector.shape[0] != EMBEDDING_DIM:
                log_warn(f"⚠️ Chunk có id={row['id']} có dimension không hợp lệ ({vector.shape[0]}), bỏ qua.")
                continue

            # Sửa lỗi Bug 2: Lấy ID trực tiếp từ cột 'id'
            faiss_id = row['id']
            vectors.append(vector)
            ids.append(faiss_id)
        except (json.JSONDecodeError, TypeError) as e:
            log_warn(f"⚠️ Lỗi xử lý embedding cho chunk id={row.get('id', 'N/A')}: {e}. Bỏ qua.")

    if not vectors:
        log_error("❌ Không có vector hợp lệ nào để thêm vào index."); return

    log_info(f"➕ Thêm {len(vectors)} vectors vào index...")
    vectors_np = np.array(vectors, dtype="float32")
    ids_np = np.array(ids, dtype="int64")

    index.add_with_ids(vectors_np, ids_np)

    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    faiss.write_index(index, INDEX_PATH)
    log_success(f"💾 Đã lưu FAISS index mới vào '{INDEX_PATH}' thành công!")
    log_info(f"✨ Index chứa tổng cộng {index.ntotal} vectors.")

if __name__ == "__main__":
    rebuild_faiss_index()
```

\</details\>
Để kiểm tra Bug 2 đã được xử lý hay chưa, bạn cần xác thực rằng **ID được lưu trong FAISS** giờ đây **trùng khớp với cột `id`** (số nguyên tự tăng) trong bảng `chunks` của SQLite.

Cách kiểm tra đơn giản và hiệu quả nhất là thực hiện hai bước sau: lấy một vài ID từ FAISS, sau đó dùng các ID đó để truy vấn trực tiếp trong SQLite.

-----

### **Bước 1: Lấy ID từ FAISS**

Bạn có thể sử dụng tệp `search_faiss_only.py` được đề cập trong tài liệu bug để thực hiện một truy vấn và xem các ID mà FAISS trả về.

  * **Hành động:** Chạy script với một câu hỏi bất kỳ.
    ```bash
    # Ví dụ, nếu bạn có tệp search_faiss_only.py
    python search_faiss_only.py "lý thái tổ là ai?"
    ```
  * **Kết quả mong đợi:** Script sẽ in ra các ID dạng số nguyên nhỏ, đơn giản.
    ```
    Querying FAISS for: "lý thái tổ là ai?"
    Top 5 FAISS IDs: [42, 15, 7, 83, 22]
    Corresponding distances: [0.89, 0.85, 0.84, 0.82, 0.81]
    ```
    **Điều quan trọng cần chú ý:** Các ID trả về phải là các số nguyên nhỏ (như `42`, `15`, `7`), chứ không phải các số cực lớn dạng hash như trước đây. Chỉ riêng việc này đã là một dấu hiệu tốt cho thấy bug đã được sửa.

-----

### **Bước 2: Đối chiếu ID trong SQLite**

Bây giờ, hãy lấy một trong các ID ở trên (ví dụ: `42`) và kiểm tra xem nó có tồn tại trong cột `id` của bảng `chunks` không.

  * **Hành động:** Bạn có thể tạo một script Python nhỏ tên `test_id.py` để kiểm tra nhanh.

    **Tạo tệp `test_id.py`:**

    ```python
    import sqlite3
    import sys

    DB_PATH = "rag_system/data/metadata.db"

    def find_chunk_by_id(chunk_id_to_find):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Truy vấn chính xác vào cột 'id'
            cursor.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id_to_find,))
            row = cursor.fetchone()
            
            print("-" * 50)
            if row:
                print(f"✅ TÌM THẤY! Dữ liệu cho chunk có id = {chunk_id_to_find}:")
                print(f"  -> Chunk ID (Text): {row['chunk_id']}")
                print(f"  -> Text: {row['text'][:100]}...") # In 100 ký tự đầu
            else:
                print(f"❌ KHÔNG TÌM THẤY chunk nào có id = {chunk_id_to_find} trong database.")
            print("-" * 50)

        except Exception as e:
            print(f"Lỗi khi truy vấn database: {e}")
        finally:
            if 'conn' in locals() and conn:
                conn.close()

    if __name__ == "__main__":
        if len(sys.argv) > 1:
            try:
                test_id = int(sys.argv[1])
                find_chunk_by_id(test_id)
            except ValueError:
                print("Lỗi: Vui lòng cung cấp một ID dạng số nguyên.")
        else:
            print("Cách dùng: python test_id.py <ID>")
            print("Ví dụ: python test_id.py 42")
    ```

    **Chạy script với ID bạn có từ Bước 1:**

    ```bash
    python test_id.py 42
    ```

  * **Kết quả mong đợi:** Script sẽ in ra thông báo tìm thấy và nội dung của chunk đó.

    ```
    --------------------------------------------------
    ✅ TÌM THẤY! Dữ liệu cho chunk có id = 42:
      -> Chunk ID (Text): lythaito-003
      -> Text: Chiếu dời đô ( Thiên đô chiếu ) ...
    --------------------------------------------------
    ```

### **Kết luận**

Nếu ID bạn lấy từ FAISS (Bước 1) có thể được tìm thấy trong cột `id` của SQLite và trả về dữ liệu (Bước 2), thì **Bug 2 đã được sửa thành công**. Phép thử cuối cùng là chạy `HybridRetriever`, nó sẽ không còn trả về kết quả rỗng nữa.
