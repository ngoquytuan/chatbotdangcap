# ingestionBetter.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ingestion module (GPU-enabled, heading-aware + semantic chunking):
- Extract to Markdown with MarkItDown (supports PDF/DOCX/MD...)
- Parse headings (H1..H6) to make sections
- Semantic chunking per section using embeddings (AITeamVN/Vietnamese_Embedding)
- GPU acceleration for embeddings if CUDA is available
- Output normalized JSON (tokens + embedding vectors ready for FAISS)

Folder layout (auto-created if missing):
  ../data/raw_documents      # input files
  ../data/ingested_json      # output JSON

Run:
  pip install -r requirements.txt
  python ingestion_module_upgraded.py
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List

from sentence_transformers import SentenceTransformer
from pyvi import ViTokenizer
from colorama import Fore, Style, init as colorama_init

import unicodedata
import re

# ==== CONFIG ====
RAW_DIR = "rag_system/data/raw_documents"
OUTPUT_DIR = "rag_system/data/ingested_json"
MODEL_NAME = "AITeamVN/Vietnamese_Embedding"
CHUNK_SIZE = 500  # số ký tự mỗi chunk
CHUNK_OVERLAP = 50
USE_GPU = True

# ==== INIT COLOR LOG ====
colorama_init(autoreset=True)
logging.basicConfig(level=logging.INFO, format="%(message)s")

def log_info(msg): logging.info(Fore.CYAN + msg + Style.RESET_ALL)
def log_success(msg): logging.info(Fore.GREEN + msg + Style.RESET_ALL)
def log_warn(msg): logging.warning(Fore.YELLOW + msg + Style.RESET_ALL)
def log_error(msg): logging.error(Fore.RED + msg + Style.RESET_ALL)

# ==== TEXT CLEANING ====
def clean_text(text: str) -> str:
    # Chuẩn hóa Unicode NFC
    text = unicodedata.normalize("NFC", text)
    # Loại bỏ BOM, zero-width space
    text = text.replace("\ufeff", "").replace("\u200b", "")
    # Thay nhiều khoảng trắng bằng 1
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# ==== TOKENIZE VIETNAMESE ====
def preprocess_vietnamese(text: str) -> str:
    text = clean_text(text)
    return ViTokenizer.tokenize(text)

# ==== CHUNKING ====
def chunk_text(text: str, size: int, overlap: int) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunk = text[start:end]
        chunks.append(chunk)
        start += size - overlap
    return chunks

# ==== FILE READING ====
def read_file(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    try:
        if ext in [".txt", ".md"]:
            return file_path.read_text(encoding="utf-8")
        elif ext == ".docx":
            import docx
            doc = docx.Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs)
        elif ext == ".pdf":
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            return "\n".join(page.get_text() for page in doc)
        else:
            log_warn(f"⚠️ Không hỗ trợ định dạng: {ext}")
            return ""
    except Exception as e:
        log_error(f"❌ Lỗi đọc file {file_path.name}: {e}")
        return ""

# ==== MAIN ====
def main():
    log_info("🚀 Khởi tạo mô hình embedding...")
    device = "cuda" if USE_GPU else "cpu"
    model = SentenceTransformer(MODEL_NAME, device=device)
    dim = model.get_sentence_embedding_dimension()
    log_success(f"✅ Model: {MODEL_NAME} | Dimension: {dim}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    files = list(Path(RAW_DIR).glob("*.*"))

    if not files:
        log_warn("⚠️ Không tìm thấy file nào trong thư mục raw_documents.")
        return

    for file in files:
        log_info(f"📂 Xử lý file: {file.name}")
        text = read_file(file)
        if not text.strip():
            log_warn(f"⚠️ File {file.name} rỗng hoặc không đọc được.")
            continue

        # Tiền xử lý tiếng Việt
        processed_text = preprocess_vietnamese(text)
        chunks = chunk_text(processed_text, CHUNK_SIZE, CHUNK_OVERLAP)

        log_info(f"✂️ Chia thành {len(chunks)} chunks.")

        embeddings = model.encode(chunks, normalize_embeddings=True, show_progress_bar=True)

        # Tạo output JSON
        output_data = {
            "document_id": file.stem,
            "title": file.name,
            "source": str(file),
            "version": "1.0",
            "language": "vi",
            "last_updated": datetime.now().isoformat(),
            "model_name": MODEL_NAME,
            "embedding_dim": dim,
            "chunks": []
        }

        for idx, (chunk_text_val, emb) in enumerate(zip(chunks, embeddings)):
            output_data["chunks"].append({
                "chunk_id": f"{file.stem}-{idx:03d}",
                "document_id": file.stem,
                "text": chunk_text_val,
                "embedding": emb.tolist()
            })

        output_path = Path(OUTPUT_DIR) / f"{file.stem}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        log_success(f"💾 Đã lưu {output_path.name}")

    log_success("🎯 Hoàn tất ingestion.")

if __name__ == "__main__":
    main()
