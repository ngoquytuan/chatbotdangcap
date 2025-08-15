import sqlite3
import sys

DB_PATH = "rag_system/data/metadata.db"

def find_chunk_by_id(chunk_id_to_find):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Truy vấn chính xác vào cột 'id'
        cursor.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id_to_find,))
        row = cursor.fetchone()

        print("-" * 50)
        if row:
            print(f"✅ TÌM THẤY! Dữ liệu cho chunk có id = {chunk_id_to_find}:")
            print(f"  -> Chunk ID (Text): {row['chunk_id']}")
            print(f"  -> Text: {row['text'][:100]}...") # In 100 ký tự đầu
        else:
            print(f"❌ KHÔNG TÌM THẤY chunk nào có id = {chunk_id_to_find} trong database.")
        print("-" * 50)

    except Exception as e:
        print(f"Lỗi khi truy vấn database: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            test_id = int(sys.argv[1])
            find_chunk_by_id(test_id)
        except ValueError:
            print("Lỗi: Vui lòng cung cấp một ID dạng số nguyên.")
    else:
        print("Cách dùng: python test_id.py <ID>")
        print("Ví dụ: python test_id.py 42")