Chắc chắn rồi. Việc tạo một tệp riêng để kiểm tra và xác thực là một ý tưởng rất hay, giúp đảm bảo hệ thống luôn ổn định.

Dưới đây là nội dung cho một tệp Python mới, bạn có thể đặt tên là `verify_embeddings.py` hoặc `check_chunks.py` như trong tài liệu của bạn. Tệp này sẽ kết nối tới cơ sở dữ liệu và kiểm tra từng bản ghi để đảm bảo cột `embedding` được lưu trữ đúng định dạng JSON.

-----

### **Tệp `verify_embeddings.py` (Nội dung mới)**

  * **Tạo một tệp mới** có tên `verify_embeddings.py` trong thư mục gốc của dự án.
  * **Dán nội dung sau vào tệp:**

<!-- end list -->

```python
# verify_embeddings.py
import sqlite3
import json
import logging
from pathlib import Path
from colorama import Fore, Style, init as colorama_init

# ==== CONFIG ====
DB_PATH = "rag_system/data/metadata.db"

# ==== INIT COLOR LOG ====
colorama_init(autoreset=True)
logging.basicConfig(level=logging.INFO, format="%(message)s")

def log_info(msg):
    logging.info(Fore.CYAN + msg + Style.RESET_ALL)

def log_success(msg):
    logging.info(Fore.GREEN + msg + Style.RESET_ALL)

def log_warn(msg):
    logging.warning(Fore.YELLOW + msg + Style.RESET_ALL)

def log_error(msg):
    logging.error(Fore.RED + msg + Style.RESET_ALL)

def verify_embedding_format():
    """
    Kiểm tra cột 'embedding' trong bảng 'chunks' để xác thực rằng
    tất cả dữ liệu được lưu dưới dạng chuỗi JSON hợp lệ.
    """
    log_info(f"🔍 Bắt đầu kiểm tra định dạng embedding trong '{DB_PATH}'...")

    db_file = Path(DB_PATH)
    if not db_file.exists():
        log_error(f"❌ Không tìm thấy file database tại: {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Lấy tất cả các chunk để kiểm tra
        cursor.execute("SELECT chunk_id, embedding FROM chunks")
        rows = cursor.fetchall()
    except Exception as e:
        log_error(f"❌ Lỗi khi kết nối hoặc đọc dữ liệu từ database: {e}")
        return
    finally:
        if 'conn' in locals() and conn:
            conn.close()

    if not rows:
        log_warn("⚠️ Không có dữ liệu trong database để kiểm tra.")
        return

    total_chunks = len(rows)
    invalid_embeddings = 0
    
    log_info(f"🔬 Đang kiểm tra {total_chunks} chunks...")

    for row in rows:
        chunk_id = row['chunk_id']
        embedding_data = row['embedding']
        
        # Thử phân tích chuỗi JSON
        try:
            # Kiểm tra xem có phải là chuỗi không
            if not isinstance(embedding_data, str):
                raise TypeError("Dữ liệu không phải là chuỗi (string).")
            # Thử parse JSON
            parsed_embedding = json.loads(embedding_data)
            # Kiểm tra xem kết quả có phải là list không
            if not isinstance(parsed_embedding, list):
                 raise TypeError("Dữ liệu JSON sau khi parse không phải là list.")

        except (json.JSONDecodeError, TypeError) as e:
            invalid_embeddings += 1
            log_warn(f"  - Lỗi chunk '{chunk_id}': Định dạng embedding không hợp lệ. Lỗi: {e}")

    log_info("-" * 40)
    log_info("📊 **KẾT QUẢ KIỂM TRA**")
    log_info(f"  - Tổng số chunks đã kiểm tra: {total_chunks}")
    
    if invalid_embeddings == 0:
        log_success(f"  ✔ Tất cả {total_chunks} embeddings đều hợp lệ và được lưu dưới dạng JSON.")
        log_success("✅ Bug đã được khắc phục hoàn toàn!")
    else:
        log_error(f"  ✖ Tìm thấy {invalid_embeddings} embedding không hợp lệ.")
        log_error("🔥 Bug vẫn còn tồn tại hoặc dữ liệu cũ chưa được dọn dẹp!")

if __name__ == "__main__":
    verify_embedding_format()

```

### **Cách sử dụng**

1.  Lưu tệp trên vào thư mục gốc dự án của bạn.
2.  Chạy nó từ terminal của bạn:
    ```bash
    python verify_embeddings.py
    ```

**Kết quả mong đợi (Nếu bug đã được fix):**

Bạn sẽ thấy một báo cáo tương tự như sau, với số embedding không hợp lệ là 0.

```
🔍 Bắt đầu kiểm tra định dạng embedding trong 'rag_system/data/metadata.db'...
🔬 Đang kiểm tra 86 chunks...
----------------------------------------
📊 **KẾT QUẢ KIỂM TRA**
  - Tổng số chunks đã kiểm tra: 86
  ✔ Tất cả 86 embeddings đều hợp lệ và được lưu dưới dạng JSON.
✅ Bug đã được khắc phục hoàn toàn!
```

Đây chính là cách xác thực cuối cùng để bạn yên tâm rằng hệ thống đang hoạt động đúng như thiết kế.