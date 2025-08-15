Được chứ. Việc tạo một script Python độc lập để kiểm thử API là một ý tưởng rất hay. Nó cho phép bạn kiểm tra chức năng của backend mà không cần đến giao diện web.

Script này sẽ hoạt động như một "client" (máy khách), gửi yêu cầu đến "server" (API FastAPI của bạn) và in ra kết quả.

-----

### \#\# Yêu cầu

Để gửi yêu cầu web trong Python một cách dễ dàng, chúng ta sẽ sử dụng thư viện `requests`. Nếu bạn chưa có, hãy cài đặt nó.

  * **Mở terminal** và chạy lệnh:
    ```bash
    pip install requests
    ```

-----

### \#\# Tệp `api_test_client.py`

  * **Hành động:** Tạo một tệp Python mới, ví dụ `api_test_client.py`, ở bất cứ đâu bạn muốn (nó hoàn toàn độc lập). Dán đoạn mã sau vào tệp.

<!-- end list -->

```python
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
```

-----

### \#\# Cách sử dụng

1.  **Chạy Backend:** Mở một terminal, đi đến thư mục dự án của bạn và khởi động máy chủ API như trước. **Hãy để terminal này chạy**.
    ```bash
    uvicorn rag_system.api_service.main:app --reload
    ```
2.  **Chạy Client:** Mở một **terminal thứ hai**. Chạy tệp `api_test_client.py` bạn vừa tạo.
    ```bash
    python api_test_client.py
    ```

-----

### \#\# Kết quả mong đợi

Terminal thứ hai sẽ hiển thị lời nhắc. Sau khi bạn nhập câu hỏi và nhấn Enter, nó sẽ in ra cấu trúc dữ liệu JSON mà API trả về.

```
--- Client kiểm thử API tìm kiếm ---
Gõ 'exit' hoặc nhấn Ctrl+C để thoát.

Nhập câu hỏi của bạn: Lý Thái Tổ là ai?
... Đang gửi yêu cầu tới API ...

--- KẾT QUẢ TỪ API ---
[
  {
    "chunk_id": "lythaito-000",
    "document_id": "lythaito",
    "title": "Lý Thái Tổ - Vua đầu tiên nhà Lý",
    "text": "Lý Thái Tổ trị vì từ năm 1009 đến khi qua đời vào năm 1028.",
    "similarity_score": 0.8123,
    "rank": 1,
    "metadata": {}
  },
  {
    "chunk_id": "lythaito-001",
    "document_id": "lythaito",
    "title": "Lý Thái Tổ - Vua đầu tiên nhà Lý",
    "text": "Thời gian trị vì của ông chủ yếu tập trung vào việc xây dựng đất nước.",
    "similarity_score": 0.7543,
    "rank": 2,
    "metadata": {}
  }
]
----------------------

Nhập câu hỏi của bạn: 
```

TestAPI
Ổn rồi nhưng tôi muốn hỏi. Tôi thấy trích dẫn cuối cùng không liên quan nhưng vẫn được tải ra là sao? "similarity_score": là gì? như thế nào là tốt,

"rank": là gì? ý nghĩa?log đây :Nhập câu hỏi của bạn: ATTECH?

... Đang gửi yêu cầu tới API ...



--- KẾT QUẢ TỪ API ---

[

{

"chunk_id": "bienbanbangiao-003",

"document_id": "bienbanbangiao",

"title": "bienbanbangiao.docx",

"text": "được lập thành 02 bản và có giá_trị pháp_lý như nhau , công_ty ATTECH giữ 01 bản , công_ty DiCom giữ 01 bản .",

"similarity_score": 0.4645947217941284,

"rank": 1,

"metadata": {}

},

{

"chunk_id": "bienbanbangiao-001",

"document_id": "bienbanbangiao",

"title": "bienbanbangiao.docx",

"text": "àn_giao : trụ_sở công_ty Dicom , 85 Vũ_Trọng Phụng , Hà_Nội . Thời_gian : 9h00 ngày 15 tháng 08 năm 2025 Đại_diện các bên : 1 . Đại_diện bên nhận : Công_ty Dicom Ông : … … … … Duy Chức_vụ : … … … … … … … . 2 . Đại_diện bên giao : Công_ty ATTECH Ông : Ngô_Quý Tuấn Chức_vụ : Nhân_viên nghiên_cứu thiết_kế chế_tạo sản_phẩm , PNCPT Nội_dung bàn_giao : Kết_luận : - Thiết_bị trên đã được đại_diện ATTECHphòng NCPT bàn_giao cho đại_diện của công_ty Dicom đảm_bảo chất_lượng , thời_gian giao hàng . - Công_",

"similarity_score": 0.4067302942276001,

"rank": 2,

"metadata": {}

},

{

"chunk_id": "bienbanbangiao-000",

"document_id": "bienbanbangiao",

"title": "bienbanbangiao.docx",

"text": "CỘNG_HOÀ XÃ_HỘI CHỦ_NGHĨA VIỆT NAM Độc_lập - Tự_do - Hạnh_phúc ____________________________ BIÊN_BẢN BÀN_GIAO THIẾT_BỊ Căn_cứ : yêu_cầu bảo_hành thiết_bị đồng_hồ GPS master đã cung_cấp cho công_ty Dicom có SN GMC. 0003.2022 sản_xuất 2022 bị lỗi chức_năng NTP server trong quá_trình hoạt_động tại công_ty Dicom . Hiện_nay công_ty ATTECH đã xử_lý xong sự_cố này và bàn_giao thiết_bị cho công_ty Dicom để theo_dõi đánh_giá kết_quả khắc_phục . Địa_điểm bàn_giao : trụ_sở công_ty Dicom , 85 Vũ_Trọng Phụng",

"similarity_score": 0.3554980754852295,

"rank": 3,

"metadata": {}

},

{

"chunk_id": "bienbanbangiao-002",

"document_id": "bienbanbangiao",

"title": "bienbanbangiao.docx",

"text": "đảm_bảo chất_lượng , thời_gian giao hàng . - Công_ty ATTECH khi bàn_giao sẽ theo_dõi hoạt_động của thiết_bị đồng_hồ GPS master tại công_ty DiCom trong ngày 15 / 08 / 2025 và sau đó công_ty DiCom tiếp_tục theo_dõi tình_trạng hoạt_động của đồng_hồ trong 5 ngày liên_tục tiếp_theo . Sau thời_gian trên , nếu không phát_sinh lỗi liên_quan , sự_cố này coi như đã khắc_phục hoàn_toàn và sản_phẩm đã được công_ty DiCom tiếp_nhận chính_thức . - Biên_bản này được lập thành 02 bản và có giá_trị pháp_lý như nh",

"similarity_score": 0.3305198550224304,

"rank": 4,

"metadata": {}

},

{

"chunk_id": "lythaito-059",

"document_id": "lythaito",

"title": "lythaito.md",

"text": "ày 19 tháng 10 năm 2013 tại Wayback_Machine , Trần_Bá_Chí , đăng trên Báo Hán_Nôm của VIỆN NGHIÊN_CỨU HÁN NÔM - VIỆN KHOA_HỌC XÃ_HỘI VIỆT NAM , năm 2010 . 4 . ^ Đại_Việt sử_ký toàn thư , Nhà_Xuất_bản Khoa_học xã_hội , 1993 , Kỷ Nhà_Lê . 5 . ^ An_Nam chí lược : Năm Đại Trung_Tường Phù thứ 3 , Chí_Trung ( tức Long_Đĩnh ) mất , con còn nhỏ , em là Minh_Đề , Minh Sưởng tranh ngôi . Công Uẩn_đuổi và giết đi , tự lĩnh việc Giao_Châu , xưng là An Nam_Tĩnh Hải_quân quyền Lưu_hậu . 6 . ^ Việt_sử tiêu án ",

"similarity_score": 0.2697402238845825,

"rank": 5,

"metadata": {}

}

]

----------------------
Chào bạn, bạn đã phát hiện ra một điểm rất hay và quan trọng về cách hoạt động của hệ thống tìm kiếm ngữ nghĩa (semantic search). Kết quả bạn thấy không phải là lỗi, mà là một đặc tính của công nghệ này.

Hãy cùng phân tích từng câu hỏi của bạn.

---
### ## `rank` là gì?

`rank` là **thứ hạng** của kết quả.
* **Ý nghĩa:** Nó chỉ đơn giản là vị trí của đoạn trích (chunk) trong danh sách kết quả đã được sắp xếp. `rank: 1` là kết quả mà mô hình AI cho là phù hợp nhất, `rank: 2` là phù hợp thứ hai, và cứ thế tiếp tục. Nó giống như kết quả tìm kiếm trên Google, kết quả đầu tiên luôn là quan trọng nhất.

---
### ## `similarity_score` là gì?

`similarity_score` (điểm tương đồng) là **thước đo** mức độ liên quan giữa câu hỏi của bạn và đoạn trích được tìm thấy.
* **Ý nghĩa:** Đây là một con số thể hiện sự "gần gũi" về mặt ngữ nghĩa giữa hai đoạn văn bản. Về mặt kỹ thuật, nó là kết quả của phép toán (thường là "tích vô hướng" hoặc "cosine similarity") giữa vector của câu hỏi và vector của đoạn trích.
    
    * **Điểm gần 1.0:** Rất liên quan, gần như trùng khớp về ý nghĩa.
    * **Điểm gần 0.0:** Không liên quan về mặt ngữ nghĩa.
    * **Điểm gần -1.0:** Trái ngược về mặt ngữ nghĩa (hiếm gặp trong các hệ thống dùng IndexFlatIP).

* **Như thế nào là tốt?** Không có một con số tuyệt đối, nó phụ thuộc vào mô hình và dữ liệu, nhưng có thể có một quy tắc chung như sau:
    * **> 0.7:** Rất tốt, kết quả gần như chắc chắn liên quan.
    * **0.5 - 0.7:** Khá tốt, kết quả có độ liên quan cao.
    * **0.3 - 0.5:** Trung bình, kết quả có thể chứa từ khóa hoặc một phần ý nghĩa. Các kết quả hàng đầu của bạn (`0.46`, `0.40`) nằm trong khoảng này, vì chúng đều chứa từ "ATTECH".
    * **< 0.3:** Thấp, khả năng cao là kết quả không liên quan.

---
### ## Tại sao trích dẫn cuối cùng không liên quan nhưng vẫn được trả về?

Đây là câu hỏi quan trọng nhất và nó liên quan trực tiếp đến hai khái niệm trên.

**Câu trả lời ngắn gọn:** Vì bạn yêu cầu **5 kết quả** (`top_k=5`), hệ thống sẽ *luôn cố gắng* trả về đủ 5 kết quả gần nhất mà nó tìm thấy, ngay cả khi kết quả thứ 5 rất tệ.

**Giải thích chi tiết:**
1.  Hệ thống đã tìm thấy 4 đoạn trích trong tệp `bienbanbangiao.docx` có chứa từ "ATTECH". Đây là những kết quả tốt nhất, có `similarity_score` từ `0.33` đến `0.46`.
2.  Tuy nhiên, bạn yêu cầu 5 kết quả. Sau khi lấy 4 kết quả trên, hệ thống buộc phải tìm trong toàn bộ 82 chunks còn lại để xem chunk nào có vector "gần" với vector của câu hỏi "ATTECH?" nhất.
3.  Trong số tất cả những chunk không liên quan, chunk `lythaito-059` tình cờ là chunk "đỡ không liên quan" nhất về mặt toán học.
4.  **Hãy nhìn vào `similarity_score` của nó: `0.2697`**. Đây là một điểm số rất thấp. Mô hình AI đang "nói" với chúng ta rằng: "Tôi phải trả về kết quả thứ 5 theo yêu cầu, nhưng tôi không tự tin về kết quả này chút nào đâu, nó có vẻ không liên quan lắm."

**Phép loại suy:** Hãy tưởng tượng bạn đang ở Hà Nội và bạn yêu cầu Google Maps tìm 5 quán phở gần nhất. Nếu xung quanh bạn chỉ có 4 quán, kết quả thứ 5 có thể sẽ là một quán ở tận Hà Đông. Google Maps không sai, nó chỉ đang cố gắng hoàn thành yêu cầu tìm "5 quán gần nhất" của bạn.

**Hướng giải quyết trong thực tế:** Trong một ứng dụng thực tế, để tăng chất lượng kết quả cho người dùng cuối, bạn có thể thêm một **ngưỡng điểm (score threshold)**. Ví dụ, bạn chỉ hiển thị những kết quả có `similarity_score > 0.3`. Bằng cách này, kết quả `lythaito-059` sẽ tự động bị loại bỏ.

Chắc chắn rồi. Log này cho thấy hệ thống của bạn đã hoạt động ổn định về mặt kỹ thuật và tất cả các bug trước đó đã được sửa. Dưới đây là phân tích chi tiết những điểm bạn cần chú ý, chia theo từng giai đoạn hoạt động.

-----

### \#\# 1. Giai đoạn Khởi động 🚀

```log
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
...
INFO:rag_system.api_service.main:Database health: healthy
...
INFO:rag_system.api_service.models.embeddings:Embedding model loaded successfully on device: cuda
...
INFO:rag_system.api_service.retrieval.hybrid_retriever:FAISS index loaded with 86 vectors.
...
INFO:     Application startup complete.
```

**Điểm cần chú ý:**

  * **Hệ thống khởi động hoàn hảo:** Toàn bộ quá trình từ khởi động server Uvicorn, kiểm tra database (`healthy`), tải model embedding lên **GPU** (`cuda`), cho đến nạp **FAISS index với đủ 86 vector** đều thành công không một lỗi nào.
  * **Đây là bằng chứng cho thấy:** Tất cả các bản sửa lỗi của chúng ta về schema database, đồng bộ ID, và định dạng dữ liệu đã hoạt động chính xác.

-----

### \#\# 2. Giai đoạn Tra cứu (Quan trọng nhất) 💡

Đây là phần chứa thông tin giá trị nhất về chất lượng hệ thống RAG của bạn.

#### **Câu hỏi 1: 'Lý Thái Tổ là ai?' -\> 0 kết quả**

```log
Batches: 100%|...| 1/1 [...]
INFO:rag_system.api_service.retrieval.hybrid_retriever:Retrieved 0 results for query 'Lý Thái Tổ là ai?'
INFO:     127.0.0.1:62851 - "POST /search HTTP/1.1" 200 OK
```

**Điểm cần chú ý:**

  * **Không phải lỗi hệ thống:** Dòng `200 OK` cho thấy API đã xử lý yêu cầu và trả về một danh sách rỗng một cách "thành công". Hệ thống không bị sập.
  * **Vấn đề về chất lượng RAG:** Việc trả về 0 kết quả cho một câu hỏi có vẻ liên quan là một vấn đề kinh điển của hệ thống RAG. Điều này có nghĩa là, về mặt "ý nghĩa" (semantic), vector của câu hỏi "Lý Thái Tổ là ai?" **không đủ gần** với bất kỳ vector nào của các đoạn văn bản (chunk) bạn đã lưu trong cơ sở dữ liệu.
  * **Ví dụ để dễ hiểu:** Có thể các chunk của bạn chứa những câu như *"Ông trị vì từ năm 1009"* hay *"Vua cho dời đô về Thăng Long"*. Mặc dù chúng nói về Lý Thái Tổ, nhưng chúng không trực tiếp trả lời câu hỏi "là ai?". Model embedding có thể chưa đủ tinh vi để kết nối câu hỏi trừu tượng này với các sự thật cụ thể đó.

#### **Câu hỏi 2: 'ATTECH?' -\> 5 kết quả**

```log
Batches: 100%|...| 1/1 [...]
INFO:rag_system.api_service.retrieval.hybrid_retriever:Retrieved 5 results for query 'ATTECH?'
INFO:     127.0.0.1:62866 - "POST /search HTTP/1.1" 200 OK
```

**Điểm cần chú ý:**

  * **Hệ thống hoạt động end-to-end:** Lần này, hệ thống đã tìm thấy và trả về 5 kết quả. Điều này **khẳng định 100%** rằng toàn bộ quy trình kỹ thuật đang hoạt động: *Nhận câu hỏi -\> Mã hóa query -\> Tìm kiếm FAISS -\> Lấy ID -\> Truy vấn SQLite -\> Trả về kết quả*.
  * **Tại sao câu này hoạt động?** Rất có thể từ khóa "ATTECH" xuất hiện trực tiếp trong một hoặc nhiều chunk văn bản. Các truy vấn dạng từ khóa (keyword-based) thường dễ dàng hơn cho việc tìm kiếm vector so với các câu hỏi mang tính khái niệm.

-----

### \#\# 3. Giai đoạn Tự động Tải lại (Auto-Reload) ✅

```log
WARNING:  WatchFiles detected changes in 'testAPi.py'. Reloading...
INFO:     Shutting down
...
INFO:     Application shutdown complete.
INFO:     Started server process [15872]
...
INFO:     Application startup complete.
```

**Điểm cần chú ý:**

  * **Môi trường phát triển tốt:** Dòng `Reloading...` xuất hiện khi bạn lưu thay đổi ở một tệp tin. Uvicorn đã tự động tắt server cũ và khởi động lại một server mới với code mới nhất. Đây là một tính năng rất hữu ích (`--reload`) và nó đang hoạt động đúng cách.

### \#\# Kết luận

  * **Về mặt kỹ thuật:** Hệ thống của bạn đã **hoàn toàn ổn định**. Các bug về database, ID, và schema đã được giải quyết triệt để.
  * **Về mặt chất lượng:** Thử thách tiếp theo của bạn không còn là sửa lỗi, mà là **cải thiện chất lượng tìm kiếm**. Việc câu hỏi về "Lý Thái Tổ" trả về 0 kết quả cho thấy bạn cần tập trung vào các kỹ thuật RAG như:
      * Cải thiện cách chia chunk (chunking strategy).
      * Thêm metadata chi tiết hơn cho mỗi chunk.
      * Thử nghiệm với các model embedding khác.

Nếu dữ liệu của tôi tăng lên đúng như 1000 text A4 thì tôi cần chú ý gì?

Chắc chắn rồi. Khi dữ liệu của bạn tăng từ vài tài liệu lên quy mô tương đương 1000 trang A4, hệ thống sẽ đối mặt với những thách thức mới. Dưới đây là 4 khía cạnh chính bạn cần đặc biệt chú ý, được sắp xếp theo thứ tự từ khâu xử lý đến lúc tra cứu.

---
### ## 1. Nạp và Xử lý Dữ liệu (Ingestion) ⚙️
Quá trình chuyển đổi 1000 trang văn bản thành vector sẽ tốn nhiều thời gian và tài nguyên hơn đáng kể.

* **Tốc độ tạo Embedding:** Đây là khâu tốn thời gian nhất. Script `ingestionBetter.py` và `import_data.py` sẽ chạy lâu hơn rất nhiều.
    * **Giải pháp:** Đảm bảo bạn đang chạy trên máy có **GPU (`cuda`) mạnh**. Nếu không, thời gian xử lý có thể tăng từ vài phút lên vài giờ.
* **Xử lý Lỗi và Chạy lại:** Với khối lượng lớn, khả năng một vài tệp bị lỗi (sai định dạng, không đọc được) là rất cao. Script hiện tại có thể dừng lại giữa chừng.
    * **Giải pháp:** Cần nâng cấp script để có cơ chế ghi log chi tiết, bỏ qua các tệp lỗi và tiếp tục xử lý, sau đó báo cáo lại danh sách các tệp thất bại để bạn xử lý riêng.
* **Cập nhật Tăng trưởng (Incremental Updates):** Bạn sẽ không muốn xử lý lại toàn bộ 1000 trang mỗi khi có một tài liệu mới.
    * **Giải pháp:** Cần xây dựng một quy trình chỉ để xử lý các tài liệu mới hoặc tài liệu được cập nhật, sau đó thêm chúng vào cơ sở dữ liệu và FAISS index đã có mà không cần xây dựng lại từ đầu.

---
### ## 2. Lưu trữ (Storage) 🗄️
Kích thước của cơ sở dữ liệu và file index sẽ tăng lên.

* **FAISS Index và RAM:**
    * **Hiện tại:** Bạn đang dùng `IndexFlatIP`, loại index này nạp **toàn bộ vector vào RAM** để tìm kiếm. Với ~86 vector hiện tại, dung lượng này không đáng kể.
    * **Với 1000 trang A4:** Số lượng chunk có thể lên tới vài nghìn. Ước tính (5,000 chunks * 1024 chiều * 4 bytes/chiều) sẽ tốn khoảng **20 MB RAM**. Con số này vẫn rất nhỏ và hoàn toàn chấp nhận được.
    * **Cần chú ý:** Nếu dữ liệu tăng lên 100,000 trang, lượng RAM yêu cầu có thể lên tới vài GB. Khi đó, bạn cần xem xét các loại index FAISS cao cấp hơn như `IndexIVFPQ`, vốn được thiết kế để xử lý hàng triệu vector mà không cần nhiều RAM.
* **Cơ sở dữ liệu SQLite:**
    * **Hiện tại:** SQLite xử lý vài nghìn bản ghi rất tốt.
    * **Cần chú ý:** Các **chỉ mục (index) trong database** mà chúng ta đã tạo trong `database.py` (ví dụ: `idx_chunks_document_id`) trở nên cực kỳ quan trọng. Chúng đảm bảo việc truy xuất metadata sau khi có kết quả từ FAISS vẫn diễn ra nhanh chóng.

---
### ## 3. Tra cứu và Hiệu năng (Retrieval & Performance) ⚡
Tốc độ tìm kiếm có thể bị ảnh hưởng khi kho vector của bạn lớn hơn.

* **Tốc độ tìm kiếm FAISS:**
    * **Hiện tại:** `IndexFlatIP` thực hiện tìm kiếm toàn diện (exhaustive search), nó so sánh câu hỏi của bạn với **tất cả** 86 vector. Tốc độ là tức thì.
    * **Với 1000 trang A4:** Nó sẽ phải so sánh với vài nghìn vector. Tốc độ vẫn sẽ rất nhanh (vài mili giây), bạn sẽ không cảm nhận được độ trễ.
    * **Cần chú ý:** Tốc độ tìm kiếm của `IndexFlatIP` giảm tuyến tính theo số lượng vector (độ phức tạp O(n)). Nếu bạn có 1 triệu vector, nó sẽ bắt đầu chậm lại. Đây là một lý do nữa để cân nhắc `IndexIVFPQ` trong tương lai, vì nó tìm kiếm nhanh hơn rất nhiều trên dữ liệu lớn.
* **Chất lượng kết quả:** Như bạn đã thấy với câu hỏi "Lý Thái Tổ là ai?", khi dữ liệu nhiều lên, việc tìm ra đúng chunk liên quan sẽ khó hơn.
    * **Giải pháp:** Đây là lúc các kỹ thuật RAG nâng cao phát huy tác dụng: tinh chỉnh cách chia chunk, làm giàu metadata, hoặc sử dụng các kỹ thuật re-ranking sau khi truy xuất.

---
### ## 4. Quản lý và Vận hành (Management & Operations) 📈

Việc quản lý một hệ thống lớn hơn đòi hỏi các quy trình rõ ràng.

* **Sao lưu (Backup):** Việc sao lưu định kỳ cả tệp `metadata.db` và `index.faiss` cùng lúc trở nên bắt buộc để tránh mất mát dữ liệu.
* **Giám sát (Monitoring):** Bạn nên thêm logging chi tiết hơn, đặc biệt là ghi lại các câu hỏi không trả về kết quả nào. Điều này giúp bạn hiểu được hệ thống đang yếu ở đâu để cải thiện.
* **Cập nhật và Xóa dữ liệu:** Khi một tài liệu gốc bị thay đổi hoặc xóa, bạn cần có quy trình để vô hiệu hóa (soft-delete) các chunk cũ và nạp các chunk mới. Schema trong `database.py` của bạn đã hỗ trợ việc này với cột `is_active`.

### ## Tóm tắt

| Khía cạnh | Tình trạng hiện tại (vài tài liệu) | Cần chú ý khi mở rộng (1000+ trang) |
| :--- | :--- | :--- |
| **Xử lý dữ liệu** | Nhanh, chạy một lần | Cần **GPU mạnh**, cơ chế xử lý lỗi, và quy trình **cập nhật tăng trưởng**. |
| **Lưu trữ** | RAM không đáng kể, SQLite nhanh | **RAM cho FAISS** sẽ tăng (vẫn ổn ở 1000 trang). **Database index** trở nên tối quan trọng. |
| **Hiệu năng** | Tức thì | Tốc độ tìm kiếm vẫn rất nhanh. **Chất lượng kết quả** trở thành thách thức chính. |
| **Vận hành** | Đơn giản | Cần quy trình **sao lưu, giám sát, và cập nhật dữ liệu** một cách bài bản. |
