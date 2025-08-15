Lỗi này xảy ra do cách bạn chạy tệp Python, không phải do lỗi logic trong mã. Lỗi `ModuleNotFoundError` xuất hiện vì khi bạn chạy một tệp tin từ bên trong một thư mục con (`scripts`), Python sẽ không tự động nhận diện được các thư mục ở cấp cao hơn (như `rag_system`).

-----

### **Nguyên nhân**

Khi bạn chạy lệnh `python .\scripts\import_data.py` từ thư mục gốc `docsearch`, Python sẽ bắt đầu thực thi từ bên trong thư mục `scripts`. Từ vị trí này, nó không thể "nhìn thấy" thư mục `rag_system` nằm cùng cấp với `scripts`.

Tưởng tượng cấu trúc thư mục của bạn là một ngôi nhà:

  * `docsearch` là ngôi nhà.
  * `scripts` và `rag_system` là hai phòng khác nhau trong nhà.

Khi bạn chạy script từ bên trong phòng `scripts`, nó không biết phòng `rag_system` tồn tại.

-----

### **Cách khắc phục**

Bạn có hai cách, nhưng tôi thực sự khuyên bạn nên dùng **Cách 1** vì đó là cách làm đúng chuẩn cho các dự án Python.

#### **Cách 1: Chạy Script như một Module (Khuyến nghị)**

Đây là cách tốt nhất. Bạn yêu cầu Python chạy script của bạn như một "module" từ thư mục gốc của dự án. Cách này sẽ thêm thư mục gốc (`docsearch`) vào đường dẫn tìm kiếm, giúp Python thấy tất cả các "căn phòng".

  * **Hành động:** Đảm bảo bạn đang ở thư mục gốc (`D:\Projects\undertest\docsearch`). Sau đó, chạy lệnh sau:

    ```bash
    python -m scripts.import_data
    ```

    **Lưu ý:**

      * Sử dụng `-m` để báo cho Python biết bạn đang chạy một module.
      * Viết đường dẫn dưới dạng `thư_mục.tên_tệp` (không có `.py`).

#### **Cách 2: Sửa Code để Tự thêm đường dẫn (Không khuyến khích)**

Cách này là một giải pháp "chữa cháy" bằng cách thêm một đoạn mã vào đầu tệp `import_data.py` để nó tự tìm đường đến thư mục gốc.

  * **Hành động:** Mở tệp `import_data.py` và thêm 3 dòng sau lên **đầu tiên** của tệp:

    ```python
    # Thêm 3 dòng này vào đầu tệp import_data.py
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Các dòng import cũ giữ nguyên
    from rag_system.api_service.utils.database import DatabaseManager
    # ...
    ```

    Sau khi thêm đoạn mã này, bạn có thể chạy lại lệnh cũ (`python .\scripts\import_data.py`) và nó sẽ hoạt động. Tuy nhiên, cách này không được coi là một thực hành tốt vì nó làm cho mã nguồn của bạn kém linh hoạt hơn.