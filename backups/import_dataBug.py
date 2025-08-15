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