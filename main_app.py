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