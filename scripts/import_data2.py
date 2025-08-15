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