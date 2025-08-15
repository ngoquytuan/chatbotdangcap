# import_data.py (FINAL, compatible with database.py)
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from colorama import Fore, Style, init as colorama_init

# Import lớp quản lý DB từ chính hệ thống của bạn
from rag_system.api_service.utils.database import DatabaseManager

# ==== CONFIG ====
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

def upsert_document(db: DatabaseManager, doc_data: Dict[str, Any]) -> None:
    """Chèn hoặc cập nhật thông tin tài liệu."""
    doc_id = doc_data['document_id']
    with db.get_cursor() as cursor:
        cursor.execute("SELECT id FROM documents WHERE document_id = ?", (doc_id,))
        exists = cursor.fetchone()

        # Dữ liệu cần chèn hoặc cập nhật
        doc_payload = {
            'document_id': doc_id,
            'title': doc_data['title'],
            'source': doc_data.get('source', 'Unknown'),
            'version': doc_data.get('version', '1.0'),
            'language': doc_data.get('language', 'vi'),
            'processing_status': 'processing' # Bắt đầu xử lý
        }

        if exists:
            # Cập nhật trạng thái nếu tài liệu đã tồn tại
            cursor.execute("""
                UPDATE documents 
                SET title = :title, source = :source, version = :version, 
                    language = :language, processing_status = :processing_status
                WHERE document_id = :document_id
            """, doc_payload)
        else:
            # Chèn mới
            cursor.execute("""
                INSERT INTO documents (document_id, title, source, version, language, processing_status)
                VALUES (:document_id, :title, :source, :version, :language, :processing_status)
            """, doc_payload)

def update_document_status(db: DatabaseManager, doc_id: str, status: str, num_chunks: int):
    """Cập nhật trạng thái sau khi xử lý xong."""
    with db.get_cursor() as cursor:
        cursor.execute("""
            UPDATE documents SET processing_status = ?, total_chunks = ? WHERE document_id = ?
        """, (status, num_chunks, doc_id))

def main():
    log_info("🚀 Khởi tạo mô hình embedding...")
    model = SentenceTransformer(MODEL_NAME, device="cuda" if USE_GPU else "cpu")
    dim = model.get_sentence_embedding_dimension()
    log_success(f"✅ Số chiều embedding: {dim}")

    log_info("📦 Khởi tạo FAISS index...")
    index = faiss.IndexFlatIP(dim)
    index = faiss.IndexIDMap2(index)

    # Sử dụng DatabaseManager từ hệ thống
    db = DatabaseManager()
    files = list(Path(JSON_DIR).glob("*.json"))
    if not files:
        log_warn("⚠️ Không tìm thấy file JSON nào."); return

    stats = {"docs": 0, "chunks_inserted": 0, "chunks_skipped": 0}

    for file in files:
        log_info(f"📂 Xử lý file: {file.name}")
        try:
            with open(file, "r", encoding="utf-8") as f: data = json.load(f)
            doc_id = data.get('document_id')
            if not doc_id:
                log_warn(f"⚠️ File {file.name} thiếu 'document_id', bỏ qua."); continue

            # Bước 1: Chèn/Cập nhật tài liệu và đặt trạng thái "processing"
            upsert_document(db, data)
            stats["docs"] += 1

            chunks_in_doc = 0
            for chunk in data.get("chunks", []):
                if "embedding" not in chunk or "chunk_id" not in chunk:
                    stats["chunks_skipped"] += 1; continue

                vec = np.array(chunk["embedding"], dtype="float32")
                if vec.shape[0] != dim:
                    stats["chunks_skipped"] += 1; continue

                # Chuẩn bị dữ liệu đầy đủ cho hàm insert_chunk của DatabaseManager
                chunk_payload = {
                    'chunk_id': chunk['chunk_id'],
                    'document_id': doc_id,
                    'title': data.get('title'),
                    'source': data.get('source'),
                    'version': data.get('version', '1.0'),
                    'language': data.get('language', 'vi'),
                    'text': chunk.get('text', ''),
                    'embedding': chunk['embedding'] # Truyền list, hàm insert_chunk sẽ xử lý
                }

                inserted_id = db.insert_chunk(chunk_payload)

                if inserted_id:
                    index.add_with_ids(vec.reshape(1, -1), np.array([inserted_id], dtype="int64"))
                    stats["chunks_inserted"] += 1
                    chunks_in_doc += 1
                else:
                    stats["chunks_skipped"] += 1

            # Bước 3: Cập nhật trạng thái document thành "completed"
            update_document_status(db, doc_id, "completed", chunks_in_doc)
            log_success(f"  ✔ Hoàn tất xử lý {doc_id} với {chunks_in_doc} chunks.")

        except Exception as e: 
            log_error(f"❌ Lỗi khi xử lý {file.name}: {e}")
            if 'doc_id' in locals():
                update_document_status(db, doc_id, "failed", 0)

    if stats["chunks_inserted"] > 0:
        os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
        faiss.write_index(index, INDEX_PATH)
        log_success(f"💾 Đã lưu FAISS index vào {INDEX_PATH}")

    db.close_connections()

    log_info("\n📊 **BÁO CÁO TỔNG KẾT**")
    log_success(f"  ✔ Documents xử lý: {stats['docs']}")
    log_success(f"  ✔ Chunks thêm mới: {stats['chunks_inserted']}")
    log_warn(f"  ⚠️ Chunks bỏ qua: {stats['chunks_skipped']}")

if __name__ == "__main__":
    main()