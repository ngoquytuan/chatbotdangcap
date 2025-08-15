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