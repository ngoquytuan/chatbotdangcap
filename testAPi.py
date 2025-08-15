import requests
import json

# URL của API backend đang chạy
API_URL = "http://127.0.0.1:8000/search"

def test_search_api():
    """
    Hàm chính để nhận input từ người dùng, gọi API và in kết quả.
    """
    print("--- Client kiểm thử API tìm kiếm ---")
    print("Gõ 'exit' hoặc nhấn Ctrl+C để thoát.")

    while True:
        try:
            # 1. Nhận câu hỏi từ người dùng
            query = input("\nNhập câu hỏi của bạn: ").strip()
            if query.lower() == 'exit':
                break
            if not query:
                continue

            # 2. Chuẩn bị dữ liệu để gửi đi (payload)
            # Dữ liệu này phải khớp với model `SearchRequest` trong FastAPI
            payload = {
                "query": query,
                "top_k": 5,
                # Bạn có thể thêm các bộ lọc khác ở đây nếu muốn
                # "document_ids": ["lythaito"], 
                # "categories": ["Lịch sử"]
            }

            print("... Đang gửi yêu cầu tới API ...")

            # 3. Gửi yêu cầu POST đến API
            response = requests.post(API_URL, json=payload)

            # Tự động báo lỗi nếu API trả về lỗi (ví dụ: 404, 500)
            response.raise_for_status()

            # 4. Lấy và in kết quả trả về
            results = response.json()
            
            print("\n--- KẾT QUẢ TỪ API ---")
            # In ra dạng JSON đẹp mắt, hỗ trợ Unicode (tiếng Việt)
            print(json.dumps(results, indent=2, ensure_ascii=False))
            print("----------------------")

        except requests.exceptions.RequestException as e:
            print(f"\nLỗi kết nối: Không thể kết nối tới API tại {API_URL}.")
            print(f"Hãy đảm bảo server FastAPI của bạn đang chạy. Lỗi chi tiết: {e}")
            break
        except KeyboardInterrupt:
            # Xử lý khi người dùng nhấn Ctrl+C
            break

    print("\n--- Kết thúc chương trình ---")

if __name__ == "__main__":
    test_search_api()