Chắc chắn rồi. Để kiểm tra `HybridRetriever` một cách rõ ràng, chúng ta sẽ tạo một tệp riêng biệt chỉ để thực hiện việc này. Tệp này sẽ khởi tạo retriever, gửi một câu truy vấn mẫu, và in kết quả ra màn hình một cách dễ đọc.

Dựa vào mã `hybrid_retriever.py` bạn cung cấp, nó phụ thuộc vào `ExtendedDatabaseManager` để truy vấn SQLite. Tệp kiểm thử dưới đây cũng sẽ giả định sự tồn tại của lớp đó.

-----

### **Tệp `search_test.py` (Nội dung mới)**

  * **Tạo một tệp mới** có tên `search_test.py` trong thư mục gốc của dự án.
  * **Dán nội dung sau vào tệp:**

<!-- end list -->

```python
# search_test.py
import logging
from sentence_transformers import SentenceTransformer
from rag_system.retrieval.hybrid_retriever import HybridRetriever
from colorama import Fore, Style, init as colorama_init

# Giả định bạn có một lớp 'ExtendedDatabaseManager' như được tham chiếu trong HybridRetriever
# Hãy đảm bảo đường dẫn import này là chính xác so với cấu trúc dự án của bạn.
try:
    from rag_system.api_service.utils.database import ExtendedDatabaseManager
except ImportError:
    print("LỖI: Không tìm thấy 'ExtendedDatabaseManager'.")
    print("Hãy đảm bảo bạn đã tạo lớp này và đường dẫn import là chính xác.")
    # Tạo một lớp giả để script có thể chạy, nhưng sẽ báo lỗi khi truy vấn
    class ExtendedDatabaseManager:
        def __init__(self, db_path):
            print(f"Lưu ý: Đang dùng ExtendedDatabaseManager giả cho {db_path}")
            self.query_builder = None
    
# ==== CONFIG ====
DB_PATH = "rag_system/data/metadata.db"
FAISS_INDEX_PATH = "rag_system/data/indexes/index.faiss"
MODEL_NAME = "AITeamVN/Vietnamese_Embedding"
USE_GPU = True

# ==== INIT COLOR AND LOGGING ====
colorama_init(autoreset=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def print_results(results):
    """Hàm in kết quả tìm kiếm một cách rõ ràng."""
    if not results:
        print(Fore.YELLOW + "--- Không tìm thấy kết quả nào. ---")
        return

    print(Fore.GREEN + f"\n--- Tìm thấy {len(results)} kết quả phù hợp ---")
    for i, res in enumerate(results):
        print(Fore.CYAN + f"\n[{i+1}] Rank: {res.get('rank', 'N/A')}")
        print(Fore.CYAN + f"    Score        : {res.get('similarity_score', 0.0):.4f}")
        print(Fore.CYAN + f"    Document     : {res.get('title', 'N/A')}")
        print(Fore.CYAN + f"    Chunk ID     : {res.get('chunk_id', 'N/A')}")
        print(Style.RESET_ALL +  f"    Text         : {res.get('text', '').strip()}...")
    print(Fore.GREEN + "\n--- Kết thúc ---")


def main():
    """
    Hàm chính để chạy kịch bản kiểm thử.
    """
    logging.info("🚀 Bắt đầu kịch bản kiểm thử cho HybridRetriever...")

    # 1. Khởi tạo các thành phần cần thiết
    logging.info(f"Tải model embedding: {MODEL_NAME}")
    device = "cuda" if USE_GPU else "cpu"
    embedding_model = SentenceTransformer(MODEL_NAME, device=device)

    logging.info(f"Kết nối tới database tại: {DB_PATH}")
    # Lưu ý: Cần có file và lớp ExtendedDatabaseManager để hoạt động
    try:
        db_manager = ExtendedDatabaseManager(DB_PATH)
        if not hasattr(db_manager, 'query_builder') or not hasattr(db_manager.query_builder, 'search_chunks_advanced'):
             logging.error("Lớp ExtendedDatabaseManager không có phương thức 'query_builder.search_chunks_advanced' cần thiết.")
             return
    except Exception as e:
        logging.error(f"Không thể khởi tạo ExtendedDatabaseManager: {e}")
        return

    logging.info(f"Tải FAISS index từ: {FAISS_INDEX_PATH}")
    retriever = HybridRetriever(
        embedding_model=embedding_model,
        db_manager=db_manager,
        faiss_index_path=FAISS_INDEX_PATH
    )

    # 2. Định nghĩa câu truy vấn
    # Dựa trên các file bạn đã nạp, câu hỏi về Lý Thái Tổ là một lựa chọn tốt
    test_query = "Lý Thái Tổ là ai?"
    logging.info(f"Thực hiện truy vấn: '{test_query}'")

    # 3. Thực hiện truy vấn và lấy kết quả
    # Chúng ta yêu cầu top 3 kết quả phù hợp nhất
    try:
        search_results = retriever.retrieve(query_text=test_query, desired_k=3)
    except Exception as e:
        logging.error(f"Lỗi xảy ra trong quá trình retrieve: {e}", exc_info=True)
        return

    # 4. In kết quả
    print_results(search_results)

if __name__ == "__main__":
    main()
```

### **Cách sử dụng**

1.  **Lưu tệp:** Lưu mã nguồn trên vào tệp `search_test.py` ở thư mục gốc của dự án.
2.  **Kiểm tra `ExtendedDatabaseManager`:** Hãy chắc chắn rằng bạn có tệp chứa lớp `ExtendedDatabaseManager` và đường dẫn import ở dòng 8 là chính xác. Đây là một thành phần quan trọng mà `HybridRetriever` của bạn cần.
3.  **Chạy từ Terminal:**
    ```bash
    python search_test.py
    ```

### **Kết quả mong đợi**

Nếu mọi thứ hoạt động chính xác, bạn sẽ thấy kết quả tương tự như sau:

```
INFO:root:🚀 Bắt đầu kịch bản kiểm thử cho HybridRetriever...
INFO:root:Tải model embedding: AITeamVN/Vietnamese_Embedding
...
INFO:root:Kết nối tới database tại: rag_system/data/metadata.db
INFO:root:Tải FAISS index từ: rag_system/data/indexes/index.faiss
...
INFO:root:HybridRetriever initialized.
INFO:root:Thực hiện truy vấn: 'Lý Thái Tổ là ai?'
INFO:root:Retrieved 3 results for query 'Lý Thái Tổ là ai?'

--- Tìm thấy 3 kết quả phù hợp ---

[1] Rank: 1
    Score        : 0.8123
    Document     : lythaito.md
    Chunk ID     : lythaito-000
    Text         : Lý Thái_Tổ ( 974 – 1028 ) , tên húy là Lý Công_Uẩn , là vị vua sáng_lập nhà Lý trong lịch_sử Việt_Nam...

[2] Rank: 2
    Score        : 0.7654
    Document     : lythaito.md
    Chunk ID     : lythaito-001
    Text         : ... Ông là người có công dời đô từ Hoa Lư ( Ninh Bình ) về thành Đại La và đổi tên thành Thăng Long ( Hà Nội ngày nay ) ...

[3] Rank: 3
    Score        : 0.6987
    Document     : some_other_doc.md
    Chunk ID     : some_other_doc-005
    Text         : ... các triều đại phong kiến Việt Nam như nhà Lý, nhà Trần đã có những đóng góp to lớn ...

--- Kết thúc ---
```

Nếu bạn nhận được kết quả (không phải là danh sách rỗng), điều đó chứng tỏ `HybridRetriever` đã hoạt động chính xác và cả hai bug đã được khắc phục thành công.