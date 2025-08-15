Không, file `ingestionBetter.py` **không cần sửa** và output bạn cung cấp là hoàn toàn chính xác.

File này đang hoạt động đúng như thiết kế.

---

### **## Phân tích chi tiết**

1.  **Chức năng của `ingestionBetter.py`:** Nhiệm vụ của script này là đọc file thô (như `.docx`, `.md`), xử lý văn bản, tạo embedding, và **xuất ra một file JSON chuẩn hóa**.
2.  **Định dạng Embedding:** Bên trong `ingestionBetter.py`, dòng code `"embedding": emb.tolist()` đã chuyển đổi vector embedding từ định dạng NumPy array sang một danh sách (list) của Python. Khi `json.dump()` được gọi, nó sẽ ghi danh sách này vào file JSON dưới dạng một mảng JSON `[0.0541..., -0.0056..., ...]`. Đây chính là định dạng chuẩn và mong muốn.
3.  **Output bạn cung cấp:** File JSON bạn gửi (`baomoi.json`) có trường `embedding` là một mảng JSON. Điều này chứng tỏ `ingestionBetter.py` đã hoàn thành xuất sắc nhiệm vụ của nó.

---

### **## Tóm tắt Luồng Dữ liệu**

Lỗi bạn gặp phải không nằm ở bước tạo ra file JSON, mà nằm ở bước *đọc file JSON đó để đưa vào database*. Luồng dữ liệu của bạn gồm 2 bước chính:

* **Bước 1: `ingestionBetter.py`**
    `File thô (.docx)` ➡️ `File JSON (với embedding là mảng)`
    Trạng thái: **Đã hoạt động chính xác ✅**

* **Bước 2: `import_data2.py`**
    `File JSON` ➡️ `SQLite Database`
    Trạng thái: **Đây là nơi có lỗi và chúng ta đã sửa 🐞➡️✅**. Script này đã đọc mảng embedding từ JSON nhưng lại lưu nó vào database dưới dạng `BLOB` (binary) thay vì `TEXT` (chuỗi JSON), gây ra lỗi `UnicodeDecodeError`.


Vì vậy, bạn không cần thay đổi gì ở `ingestionBetter.py`. Những gì chúng ta đã làm ở các bước trước là sửa `import_data2.py` để nó xử lý đúng định dạng JSON mà `ingestionBetter.py` đã tạo ra.

# Technical Requirements: Ingestion Module (ingestionBetter.py)

## 1. Introduction

This document outlines the technical requirements for the ingestion module, implemented in `ingestionBetter.py`. This module is responsible for reading raw documents, processing their content, generating embeddings, and outputting a normalized JSON format suitable for downstream tasks like semantic search.

## 2. Functional Requirements

*   **Document Reading:** The module must be able to read and extract text from the following document types:
    *   `.txt`
    *   `.md`
    *   `.docx`
    *   `.pdf`
*   **Text Processing:**
    *   Clean the extracted text by:
        *   Normalizing Unicode to NFC form.
        *   Removing Byte Order Marks (BOM) and zero-width spaces.
        *   Replacing multiple whitespace characters with single spaces.
        *   Stripping leading/trailing whitespace.
    *   Tokenize Vietnamese text using the `pyvi` library.
*   **Chunking:** Divide the processed text into chunks of a configurable size (`CHUNK_SIZE`) with a configurable overlap (`CHUNK_OVERLAP`).
*   **Embedding Generation:**
    *   Generate embeddings for each text chunk using the specified sentence transformer model (`MODEL_NAME`).
    *   Support GPU acceleration for embedding generation if CUDA is available (`USE_GPU`).
    *   Normalize the embeddings.
*   **JSON Output:**
    *   Output a JSON file containing the following information:
        *   `document_id`: The filename (without extension) of the original document.
        *   `title`: The filename of the original document.
        *   `source`: The full path to the original document.
        *   `version`:  A version number for the data format (currently "1.0").
        *   `language`: The language of the document (currently "vi" for Vietnamese).
        *   `last_updated`: The timestamp of when the data was processed.
        *   `model_name`: The name of the sentence transformer model used.
        *   `embedding_dim`: The dimensionality of the embeddings.
        *   `chunks`: A list of chunks, each containing:
            *   `chunk_id`: A unique identifier for the chunk.
            *   `document_id`: The ID of the document the chunk belongs to.
            *   `text`: The text content of the chunk.
            *   `embedding`: A list representing the embedding vector for the chunk.

## 3. Non-Functional Requirements

*   **Performance:** The module should process documents efficiently, leveraging GPU acceleration when available.
*   **Error Handling:** The module should handle file reading errors gracefully and log informative error messages.
*   **Configuration:** The module should be configurable through variables for:
    *   Raw document directory (`RAW_DIR`)
    *   Output directory (`OUTPUT_DIR`)
    *   Sentence transformer model name (`MODEL_NAME`)
    *   Chunk size (`CHUNK_SIZE`)
    *   Chunk overlap (`CHUNK_OVERLAP`)
    *   GPU usage (`USE_GPU`)
*   **Logging:** The module should provide informative logging messages to track its progress and any errors encountered.

## 4. Dependencies

*   Python 3.x
*   `sentence-transformers`
*   `pyvi`
*   `docx` (for .docx files)
*   `fitz` (PyMuPDF for .pdf files)
*   `colorama`
*   `json`
*   `os`
*   `pathlib`
*   `datetime`
*   `logging`

## 5. File Structure

*   `RAW_DIR`:  Stores the input documents.
*   `OUTPUT_DIR`: Stores the generated JSON files.

## 6. Usage

1.  Install dependencies: `pip install -r requirements.txt`
2.  Run the script: `python ingestionBetter.py`

## 7. Sample JSON Output

```json
{
  "document_id": "baomoi",
  "title": "baomoi.docx",
  "source": "rag_system/data/raw_documents/baomoi.docx",
  "version": "1.0",
  "language": "vi",
  "last_updated": "2025-08-15T10:03:00.000Z",
  "model_name": "AITeamVN/Vietnamese_Embedding",
  "embedding_dim": 768,
  "chunks": [
    {
      "chunk_id": "baomoi-000",
      "document_id": "baomoi",
      "text": "Đây là chunk văn bản đầu tiên...",
      "embedding": [
        0.0541,
        -0.0056,
        ...
      ]
    },
    {
      "chunk_id": "baomoi-001",
      "document_id": "baomoi",
      "text": "Đây là chunk văn bản thứ hai...",
      "embedding": [
        -0.0123,
        0.0456,
        ...
      ]
    }
  ]
}
