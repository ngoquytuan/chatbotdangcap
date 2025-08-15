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