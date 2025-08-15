Chính xác, bạn hiểu rất đúng. Tệp `search_test.py` là một "entry point" (điểm khởi đầu) để bạn chạy và kiểm tra nội bộ, nhưng nó không phải là cách tốt nhất để các module khác gọi đến.

Để các module khác có thể sử dụng chức năng tìm kiếm này một cách chuyên nghiệp, bạn nên tạo ra một **lớp dịch vụ (Service Class)** hoặc một **API đơn giản**. Cách làm này giúp đóng gói logic, quản lý tài nguyên (như model) hiệu quả và cung cấp một giao diện (interface) rõ ràng cho các module khác.

Dưới đây là cách thực hiện từng bước.

-----

### \#\# Bước 1: Tạo Lớp Dịch vụ Tìm kiếm (Search Service)

Chúng ta sẽ tạo một file mới để định nghĩa một lớp `SearchService`. Lớp này sẽ chịu trách nhiệm khởi tạo mọi thứ cần thiết (model, retriever) và cung cấp một phương thức `search` đơn giản.

  * **Tạo một file mới** tại `rag_system/api_service/search_service.py`

  * **Dán nội dung sau vào file:**

    ```python
    # rag_system/api_service/search_service.py
    import logging
    from typing import List, Dict, Any

    # Import các thành phần cần thiết từ hệ thống của bạn
    from .utils.database import extended_db
    from .models.embeddings import get_embedding_model
    from .retrieval.hybrid_ retriever import HybridRetriever

    logger = logging.getLogger(__name__)

    class SearchService:
        """
        Lớp dịch vụ đóng gói toàn bộ logic tìm kiếm.
        Khởi tạo một lần và tái sử dụng ở nhiều nơi.
        """
        _instance = None

        def __new__(cls, *args, **kwargs):
            # Sử dụng Singleton pattern để đảm bảo model chỉ được load một lần duy nhất
            if not cls._instance:
                cls._instance = super(SearchService, cls).__new__(cls)
            return cls._instance

        def __init__(self):
            # Biến này để đảm bảo logic init chỉ chạy một lần
            if hasattr(self, '_initialized') and self._initialized:
                return
            
            logger.info("Khởi tạo SearchService...")
            self.embedding_model = get_embedding_model()
            self.retriever = HybridRetriever(
                embedding_model=self.embedding_model,
                db_manager=extended_db,
                faiss_index_path="rag_system/data/indexes/index.faiss"
            )
            logger.info("SearchService đã sẵn sàng.")
            self._initialized = True

        def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
            """
            Phương thức chính để thực hiện tìm kiếm.
            Các module khác sẽ gọi phương thức này.
            """
            if not query or not isinstance(query, str):
                logger.warning("Câu hỏi không hợp lệ.")
                return []
            
            logger.info(f"Thực hiện tìm kiếm cho câu hỏi: '{query}'")
            results = self.retriever.retrieve(query_text=query, desired_k=top_k)
            return results

    # Tạo một instance toàn cục (global instance) để dễ dàng import và sử dụng
    search_service = SearchService()

    ```

-----

### \#\# Bước 2: Cách Module Khác Gọi Đến

Bây giờ, bất kỳ module nào khác trong dự án của bạn (ví dụ như một file API, một ứng dụng web, hoặc một script khác) đều có thể sử dụng chức năng tìm kiếm một cách cực kỳ đơn giản.

Giả sử bạn có một file `main_app.py` ở thư mục gốc:

```python
# main_app.py
import json
from rag_system.api_service.search_service import search_service

def handle_user_request(user_question: str):
    """
    Ví dụ về một hàm xử lý yêu cầu của người dùng.
    """
    print(f"\n--- Nhận yêu cầu từ người dùng: '{user_question}' ---")
    
    # Chỉ cần gọi phương thức search từ service đã được import
    search_results = search_service.search(user_question)

    if search_results:
        print("\n=== KẾT QUẢ TỪ SEARCH SERVICE ===")
        for r in search_results:
            print(f"[{r['rank']}] {r['title']} - {r['chunk_id']}")
            print(f"  Score: {r['similarity_score']:.4f}")
            print(f"  Text: {r['text'][:100]}...") # In rút gọn
    else:
        print("Không tìm thấy kết quả phù hợp.")

if __name__ == "__main__":
    # Lần đầu tiên gọi, SearchService sẽ được khởi tạo (tốn thời gian load model)
    handle_user_request("Lý Thái Tổ là ai?")
    
    # Từ lần thứ hai trở đi, nó sẽ chạy ngay lập tức vì model đã được load
    handle_user_request("Chiếu dời đô có nội dung gì?")

```

### \#\# Lợi ích của phương pháp này

1.  **Hiệu quả (Efficiency):** `embedding_model` là một thành phần nặng và tốn thời gian để tải. Với kiến trúc này, nó chỉ được **tải vào bộ nhớ một lần duy nhất** khi `SearchService` được khởi tạo lần đầu. Mọi lệnh gọi `search` sau đó đều tái sử dụng model đã có sẵn.
2.  **Dễ sử dụng (Easy to Use):** Các module khác không cần quan tâm đến `HybridRetriever`, `extended_db`, hay `faiss_index_path`. Chúng chỉ cần import `search_service` và gọi `search("câu hỏi...")`.
3.  **Tách biệt logic (Separation of Concerns):** Logic tìm kiếm được đóng gói gọn gàng ở một nơi. Nếu sau này bạn muốn thay đổi cách tìm kiếm (ví dụ thêm một bộ lọc mới), bạn chỉ cần sửa ở `SearchService` mà không ảnh hưởng đến các module khác.
4.  **Dễ bảo trì và mở rộng:** Kiến trúc này giúp dự án của bạn trở nên rõ ràng, dễ hiểu và dễ dàng thêm các chức năng mới trong tương lai.