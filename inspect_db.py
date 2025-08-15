# inspect_db.py (FIXED to be compatible with database.py)
# Nó sẽ kết nối đúng cách và hiển thị dữ liệu từ bảng chunks nếu có.
import sys
import os

# Đảm bảo Python có thể tìm thấy các module trong dự án
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rag_system.api_service.utils.database import extended_db

def main():
    """
    Kết nối tới DB và in ra thông tin của các chunk để kiểm tra.
    """
    print("--- Bắt đầu kiểm tra nội dung bảng 'chunks' ---")
    
    # Sử dụng context manager để quản lý kết nối và cursor một cách an toàn
    try:
        with extended_db.get_cursor() as cursor:
            # Câu lệnh SQL vẫn giữ nguyên vì các cột này đều tồn tại trong schema mới
            cursor.execute("""
                SELECT id, chunk_id, document_id, title, is_active, invalidated_by, 
                       LENGTH(embedding) as embedding_len, metadata
                FROM chunks
                ORDER BY id ASC
            """)
            rows = cursor.fetchall()

        print(f"\nTổng số chunks trong DB: {len(rows)}\n")
        
        if not rows:
            print("Bảng 'chunks' đang trống.")
            return

        for row in rows:
            # Truy cập dữ liệu bằng tên cột thay vì chỉ số
            chunk_id = row['chunk_id']
            doc_id = row['document_id']
            title = row['title']
            is_active = row['is_active']
            invalidated_by = row['invalidated_by']
            embedding_len = row['embedding_len']
            metadata = row['metadata']

            print(f"ID: {row['id']} | chunk_id: {chunk_id} | doc_id: {doc_id}")
            print(f"  Title: {title}")
            print(f"  is_active: {is_active} | invalidated_by: {invalidated_by}")
            print(f"  embedding length: {embedding_len}")
            print(f"  metadata: {metadata}")
            print("-" * 60)

    except Exception as e:
        print(f"\nĐã xảy ra lỗi khi truy vấn database: {e}")
        print("Vui lòng kiểm tra lại xem database đã được tạo và có dữ liệu chưa.")

    finally:
        # Không cần conn.close() vì context manager đã tự xử lý
        print("\n--- Kết thúc kiểm tra ---")


if __name__ == "__main__":
    main()