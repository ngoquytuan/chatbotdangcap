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