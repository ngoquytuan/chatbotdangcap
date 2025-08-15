Chắc chắn rồi. Dưới đây là toàn bộ nội dung cho tệp `import_data2.py` đã được sửa lỗi và tệp `rebuild_index.py` được tạo mới để bạn sử dụng.

-----

### **1. Tệp `import_data2.py` (Đã sửa lỗi)**

Đây là toàn bộ nội dung của tệp `import_data2.py`. Bạn chỉ cần sao chép và ghi đè lên tệp cũ của mình. Thay đổi quan trọng nằm ở dòng 56, nơi chúng tôi chuyển đổi embedding thành chuỗi JSON trước khi lưu.

```python
# import_data2.py
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
MODEL_NAME = "AITeamVN/Vietnamese_Embedding" # Cần cho việc lấy số chiều embedding
USE_GPU = True  # True nếu muốn GPU

# ==== INIT COLOR LOG ====
colorama_init(autoreset=True)
logging.basicConfig(level=logging.INFO, format="%(message)s")

def log_info(msg):
    logging.info(Fore.CYAN + msg + Style.RESET_ALL)

def log_success(msg):
    logging.info(Fore.GREEN + msg + Style.RESET_ALL)

def log_warn(msg):
    logging.warning(Fore.YELLOW + msg + Style.RESET_ALL)

def log_error(msg):
    logging.error(Fore.RED + msg + Style.RESET_ALL)

# ==== DB MANAGER ====
class DBManager:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.ensure_schema()

    def ensure_schema(self):
        # Sử dụng TEXT cho embedding để lưu chuỗi JSON
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT,
                text TEXT,
                embedding TEXT
            )
        """)
        self.conn.commit()

    def insert_chunk(self, chunk: Dict[str, Any]) -> bool:
        try:
            # FIX: Chuyển đổi numpy array thành list, sau đó thành chuỗi JSON
            embedding_json = json.dumps(chunk["embedding"].tolist())
            self.conn.execute("""
                INSERT OR IGNORE INTO chunks (chunk_id, document_id, text, embedding)
                VALUES (?, ?, ?, ?)
            """, (
                chunk["chunk_id"],
                chunk["document_id"],
                chunk["text"],
                embedding_json # Lưu chuỗi JSON
            ))
            self.conn.commit()
            return True
        except Exception as e:
            log_error(f"Lỗi insert chunk {chunk['chunk_id']}: {e}")
            return False

    def chunk_exists(self, chunk_id: str) -> bool:
        cur = self.conn.execute("SELECT 1 FROM chunks WHERE chunk_id = ?", (chunk_id,))
        return cur.fetchone() is not None

    def close(self):
        self.conn.close()

# ==== MAIN IMPORT FUNCTION ====
def main():
    log_info("🚀 Khởi tạo mô hình embedding để lấy số chiều...")
    device = "cuda" if USE_GPU else "cpu"
    model = SentenceTransformer(MODEL_NAME, device=device)
    dim = model.get_sentence_embedding_dimension()
    log_success(f"✅ Số chiều embedding: {dim}")

    # Khởi tạo FAISS index
    log_info("📦 Khởi tạo FAISS index...")
    # Dùng IndexFlatIP (Inner Product) vì embedding đã được chuẩn hóa (normalize_embeddings=True trong ingestion)
    index = faiss.IndexFlatIP(dim) 
    index = faiss.IndexIDMap2(index)

    # Kết nối DB
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
                stats["files_err"] += 1
                continue

            for chunk in data["chunks"]:
                chunk_id = chunk.get("chunk_id")
                if not chunk_id or "embedding" not in chunk:
                    log_warn(f"⚠️ Chunk trong {file.name} thiếu dữ liệu bắt buộc (chunk_id, embedding).")
                    stats["chunks_skipped"] += 1
                    continue

                if db.chunk_exists(chunk_id):
                    log_warn(f"⚠️ Chunk {chunk_id} đã tồn tại, bỏ qua.")
                    stats["chunks_skipped"] += 1
                    continue
                
                vec = np.array(chunk["embedding"], dtype="float32")
                if vec.shape[0] != dim:
                    log_warn(f"⚠️ Chunk {chunk_id} có dimension {vec.shape[0]} ≠ {dim}, bỏ qua.")
                    stats["chunks_skipped"] += 1
                    continue

                # Tạo ID cho FAISS từ hash của chunk_id
                # Dùng modulo để đảm bảo ID nằm trong phạm vi của int64
                faiss_id = hash(chunk_id) % (2**63 - 1)
                
                # Thêm vào DB và FAISS index
                if db.insert_chunk({
                    "chunk_id": chunk_id,
                    "document_id": chunk.get("document_id", ""),
                    "text": chunk.get("text", ""),
                    "embedding": vec
                }):
                    # FAISS yêu cầu vector phải là 2D array
                    index.add_with_ids(vec.reshape(1, -1), np.array([faiss_id], dtype="int64"))
                    stats["chunks_inserted"] += 1
                else:
                    # Nếu insert vào DB lỗi thì cũng không thêm vào FAISS
                    stats["chunks_skipped"] += 1


            stats["files_ok"] += 1

        except Exception as e:
            log_error(f"❌ Lỗi khi xử lý {file.name}: {e}")
            stats["files_err"] += 1

    # Lưu FAISS index
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

-----

### **2. Tệp `rebuild_index.py` (Nội dung mới)**

Đây là một script hoàn toàn mới giúp bạn xây dựng lại tệp `index.faiss` từ cơ sở dữ liệu `metadata.db` đã được sửa lỗi. Điều này rất hữu ích khi tệp index bị hỏng hoặc cần được tạo lại mà không cần phải chạy lại toàn bộ quá trình ingestion.

  * **Tạo một tệp mới** có tên `rebuild_index.py` trong thư mục gốc của dự án của bạn.
  * **Dán nội dung sau vào tệp:**

<!-- end list -->

```python
# rebuild_index.py
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
# Lấy từ file readme.json hoặc từ model.get_sentence_embedding_dimension()
EMBEDDING_DIM = 1024 

# ==== INIT COLOR LOG ====
colorama_init(autoreset=True)
logging.basicConfig(level=logging.INFO, format="%(message)s")

def log_info(msg):
    logging.info(Fore.CYAN + msg + Style.RESET_ALL)

def log_success(msg):
    logging.info(Fore.GREEN + msg + Style.RESET_ALL)

def log_warn(msg):
    logging.warning(Fore.YELLOW + msg + Style.RESET_ALL)

def log_error(msg):
    logging.error(Fore.RED + msg + Style.RESET_ALL)

def rebuild_faiss_index():
    """
    Đọc tất cả các chunk từ SQLite và xây dựng lại FAISS index.
    """
    log_info(f"🔍 Bắt đầu quá trình xây dựng lại FAISS index từ '{DB_PATH}'...")

    db_file = Path(DB_PATH)
    if not db_file.exists():
        log_error(f"❌ Không tìm thấy file database tại: {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT chunk_id, embedding FROM chunks")
        rows = cursor.fetchall()
    except Exception as e:
        log_error(f"❌ Lỗi khi đọc dữ liệu từ database: {e}")
        return
    finally:
        if 'conn' in locals() and conn:
            conn.close()

    if not rows:
        log_warn("⚠️ Không có dữ liệu trong database để xây dựng index.")
        return

    log_info(f"📚 Tìm thấy {len(rows)} chunks trong database.")

    # Khởi tạo FAISS index
    log_info(f"📦 Khởi tạo FAISS index với dimension: {EMBEDDING_DIM}")
    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    index = faiss.IndexIDMap2(index)

    vectors = []
    ids = []

    for row in rows:
        try:
            # FIX: Đọc chuỗi JSON từ DB, chuyển thành list, rồi thành numpy array
            embedding_list = json.loads(row['embedding'])
            vector = np.array(embedding_list, dtype="float32")
            
            # Kiểm tra số chiều
            if vector.shape[0] != EMBEDDING_DIM:
                log_warn(f"⚠️ Chunk {row['chunk_id']} có dimension không hợp lệ ({vector.shape[0]}), bỏ qua.")
                continue

            # Tạo FAISS ID từ hash của chunk_id, đồng bộ với logic của import_data2.py
            faiss_id = hash(row['chunk_id']) % (2**63 - 1)

            vectors.append(vector)
            ids.append(faiss_id)

        except (json.JSONDecodeError, TypeError) as e:
            log_warn(f"⚠️ Lỗi khi xử lý embedding cho chunk {row['chunk_id']}: {e}. Bỏ qua.")
            continue
    
    if not vectors:
        log_error("❌ Không có vector hợp lệ nào để thêm vào index.")
        return

    log_info(f"➕ Thêm {len(vectors)} vectors vào index...")
    
    # Chuyển đổi list thành numpy array 2D
    vectors_np = np.array(vectors, dtype="float32")
    ids_np = np.array(ids, dtype="int64")

    # Thêm vào index
    index.add_with_ids(vectors_np, ids_np)

    # Lưu FAISS index
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    faiss.write_index(index, INDEX_PATH)
    log_success(f"💾 Đã lưu FAISS index mới vào '{INDEX_PATH}' thành công!")
    log_info(f"✨ Index chứa tổng cộng {index.ntotal} vectors.")

if __name__ == "__main__":
    rebuild_faiss_index()

```

Bây giờ, quy trình làm việc của bạn sẽ là:

1.  **Một lần duy nhất:** Xóa `metadata.db` và `index.faiss` cũ.
2.  Chạy `python import_data2.py` để nhập dữ liệu với định dạng lưu trữ chính xác.
3.  **Bất cứ khi nào cần:** Chạy `python rebuild_index.py` để tạo lại tệp `index.faiss` từ dữ liệu đã có trong `metadata.db`.

Vâng, tệp **`init_db.py` này rất liên quan** và là một phần quan trọng trong hệ thống của bạn.

Việc bạn đưa ra tệp này giúp làm rõ hơn về cấu trúc hoàn chỉnh của cơ sở dữ liệu.

-----

### **Tại sao tệp `init_db.py` lại liên quan?**

1.  **Định nghĩa Cấu trúc Bảng (Schema):** Tệp này chứa mã SQL để tạo bảng `chunks` với đầy đủ các cột và các chỉ mục (index) để tối ưu hóa truy vấn. Script `import_data2.py` trước đây chỉ tạo một bảng đơn giản với 4 cột, trong khi `init_db.py` tạo ra một cấu trúc hoàn chỉnh và bền vững hơn.

2.  **Xác nhận Kiểu dữ liệu `embedding`:** Quan trọng nhất, trong `CREATE_CHUNKS_TABLE_SQL`, cột `embedding` được định nghĩa là `TEXT`. Điều này hoàn toàn chính xác và **khớp với giải pháp** chúng ta đã thực hiện ở tệp `import_data2.py` (lưu trữ embedding dưới dạng chuỗi JSON). Lỗi không nằm ở cấu trúc bảng, mà ở cách dữ liệu được chèn vào.

-----

### **Quy trình làm việc được đề xuất**

Với sự có mặt của `init_db.py`, quy trình chuẩn để thiết lập lại cơ sở dữ liệu của bạn nên như sau:

1.  **Xóa cơ sở dữ liệu cũ (nếu có):** Để bắt đầu lại một cách sạch sẽ.

    ```bash
    del rag_system\data\metadata.db
    ```

2.  **Chạy `init_db.py` để tạo cơ sở dữ liệu:** Bước này sẽ tạo tệp `metadata.db` với cấu trúc bảng hoàn chỉnh.

    ```bash
    python init_db.py
    ```

    Bạn sẽ thấy thông báo: `Database 'rag_system/data/metadata.db' initialized successfully.`

3.  **Chạy `import_data2.py` đã sửa lỗi:** Bước này sẽ điền dữ liệu vào các bảng đã được tạo ở trên.

    ```bash
    python import_data2.py
    ```

**Lưu ý:** Tệp `import_data2.py` của bạn chỉ chèn dữ liệu vào 4 cột (`chunk_id`, `document_id`, `text`, `embedding`). Điều này vẫn hoàn toàn hoạt động tốt với bảng được tạo bởi `init_db.py`, vì các cột còn lại đã được gán giá trị mặc định (ví dụ: `version TEXT DEFAULT "1.0"`) trong câu lệnh `CREATE TABLE`.


(venvTest) PS D:\Projects\undertest\docsearch> python.exe .\scripts\init_db.py
Database 'rag_system/data/metadata.db' initialized successfully.
🚀 Khởi tạo mô hình embedding để lấy số chiều...
Load pretrained SentenceTransformer: AITeamVN/Vietnamese_Embedding
✅ Số chiều embedding: 1024
📦 Khởi tạo FAISS index...
📂 Xử lý file: bienbanbangiao.json
📂 Xử lý file: lythaito.json
📂 Xử lý file: readme.json
📂 Xử lý file: vinacap.json
📂 Xử lý file: baomoi.json
💾 Đã lưu FAISS index vào rag_system/data/indexes/index.faiss
📊 **BÁO CÁO TỔNG KẾT**
  ✔ Files thành công: 5
  ✖ Files lỗi: 0
  ✔ Chunks thêm mới: 86
  ⚠️ Chunks bỏ qua: 0
(venvTest) PS D:\Projects\undertest\docsearch> python.exe .\scripts\rebuild_index.py
🔍 Bắt đầu quá trình xây dựng lại FAISS index từ 'rag_system/data/metadata.db'...
📚 Tìm thấy 86 chunks trong database.
📦 Khởi tạo FAISS index với dimension: 1024
➕ Thêm 86 vectors vào index...
💾 Đã lưu FAISS index mới vào 'rag_system/data/indexes/index.faiss' thành công!
✨ Index chứa tổng cộng 86 vectors.


Vâng, dựa trên kết quả bạn cung cấp, có thể khẳng định **mọi thứ đã hoạt động hoàn hảo**! 👍

---

### **Tại sao chúng ta có thể chắc chắn?**

1.  **Khởi tạo và Nạp dữ liệu thành công:** Lần chạy đầu tiên (`init_db.py` theo sau bởi `import_data2.py`) đã tạo cơ sở dữ liệu và nạp 86 chunks mà không gặp lỗi. Điều quan trọng là các vector embedding giờ đã được lưu dưới dạng chuỗi JSON, đúng như chúng ta đã sửa.

2.  **`rebuild_index.py` là bằng chứng cuối cùng:**
    * Script này đã đọc thành công 86 chunks **từ cơ sở dữ liệu `metadata.db`**.
    * Nó đã chuyển đổi các chuỗi JSON embedding trở lại thành vector mà không gây ra lỗi `UnicodeDecodeError`.
    * Nó đã xây dựng lại tệp `index.faiss` với đủ 86 vector.

Sự thành công của `rebuild_index.py` chính là phép thử xác nhận rằng bug ban đầu đã được giải quyết triệt để. Dữ liệu trong cơ sở dữ liệu của bạn giờ đây đã nhất quán và có thể được sử dụng bởi các thành phần khác trong hệ thống.

Chúc mừng bạn đã sửa lỗi thành công! 🚀