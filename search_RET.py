# search_test.py
import logging
from sentence_transformers import SentenceTransformer
from rag_system.api_service.retrieval.hybrid_retriever import HybridRetriever
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