# Báo cáo nộp bài Lab W2-D2: Root Cause Analysis (RCA)

---

## Câu hỏi 1: Confidence của top-1 trong cluster lớn nhất em xử lý là bao nhiêu? Nếu phải set threshold để auto-rollback (không cần SRE confirm), em chọn số nào? Vì sao?

### Câu trả lời

* **Confidence của top-1 trong cụm lớn nhất:**

  * Cụm lớn nhất mà hệ thống xử lý trong bài lab là `c-000-000` (15 alerts, liên quan đến 6 dịch vụ trong khoảng thời gian `09:42:01Z` - `09:46:01Z`).
  * Sau khi tối ưu thuật toán, chỉ số confidence của root cause hàng đầu là **`payment-svc`** đạt **`0.97`**.
  * Kết quả này hoàn toàn trùng khớp với ground truth của dataset. `payment-svc` gặp tình trạng cạn kiệt DB connection pool (`db_connection_pool_used_ratio = 0.99`) tại `09:42:18`, dẫn đến độ trễ tăng cao và tạo hiệu ứng lan truyền lỗi sang `checkout-svc`, sau đó ảnh hưởng tiếp đến `edge-lb`.

* **Ngưỡng threshold đề xuất cho auto-rollback:**

  * Em lựa chọn ngưỡng **`0.85`** để kích hoạt auto-remediation mà không cần SRE xác nhận.

### Lý do

1. **Thuật toán đã được cải thiện đáng kể**

   Em đã chuyển sang chạy PageRank trên đồ thị APM gốc, kết hợp thêm chỉ số `Topology Diff (in_degree - out_degree)` và cơ chế lọc timestamp theo từng cluster. Các cải tiến này giúp giảm đáng kể nguy cơ nhận diện nhầm service bị ảnh hưởng thành root cause.

2. **Phân tách rõ ràng giữa các trường hợp chắc chắn và không chắc chắn**

   * Những cluster có sự đồng thuận cao giữa Graph Analysis, Alert Timeline và dữ liệu lịch sử từ RAG thường đạt confidence trên `0.85`, ví dụ:

     * `c-000-000`: confidence `0.97`
     * `c-002-000`: confidence `0.89`

   * Ngược lại, các cluster có topology rời rạc hoặc chứa tín hiệu nhiễu như `c-001-000` chỉ đạt confidence khoảng `0.78`, từ đó sẽ được chuyển cho SRE xem xét thủ công thay vì tự động rollback.

Theo em, ngưỡng `0.85` là điểm cân bằng hợp lý giữa tốc độ khắc phục sự cố và độ an toàn khi vận hành production.

---

## Câu hỏi 2: Variant em chọn cho classifier là gì? Chạy thực tế ra sao? Trade-off với các variant còn lại?

### Câu trả lời

* **Variant lựa chọn:** `C. Paid LLM`
* **Mô hình sử dụng:** `gpt-5.4-mini`

### Kết quả thực tế

1. **Độ trễ xử lý**

   Mỗi cluster mất khoảng `1.8 - 2.5 giây` để hoàn thành các bước Retrieval, Prompt Construction và LLM Inference. Đây là thành phần có độ trễ lớn nhất trong pipeline.

2. **Độ ổn định đầu ra**

   Nhờ sử dụng JSON Mode (`response_format={"type":"json_object"}`), hệ thống không gặp lỗi parse JSON trong quá trình thử nghiệm.

3. **Kết quả phân loại**

   * `c-000-000` → `connection_pool_exhaustion` (confidence `0.97`)
   * `c-001-000` → `deadlock` (confidence `0.78`)
   * `c-002-000` → `connection_pool_exhaustion` (confidence `0.89`)

### Trade-off với các phương án khác

| Tiêu chí          | Paid LLM (Đã chọn)   | Rule-based        | Local/Free LLM   |
| ----------------- | -------------------- | ----------------- | ---------------- |
| Latency           | ~2 giây              | < 5 ms            | 3 - 8 giây       |
| Chi phí           | Có chi phí API       | Không tốn chi phí | Tốn chi phí GPU  |
| Khả năng suy luận | Rất tốt              | Hạn chế           | Trung bình       |
| Bảo mật dữ liệu   | Gửi dữ liệu ra cloud | Chạy local        | Chạy local       |
| Định dạng JSON    | Rất ổn định          | Ổn định tuyệt đối | Dễ phát sinh lỗi |

Theo em, Rule-based rất nhanh nhưng khó mở rộng khi xuất hiện các mẫu sự cố mới. Local LLM đảm bảo dữ liệu nội bộ nhưng yêu cầu hạ tầng GPU và thường kém ổn định hơn trong việc sinh JSON. Paid LLM mang lại sự cân bằng tốt nhất giữa độ chính xác, khả năng suy luận và chi phí triển khai.

---

## Câu hỏi 3: Đọc bảng Industry Landscape (§6) — pipeline em xây gần với sản phẩm nào nhất? Trong domain GeekShop, lựa chọn đó có hợp lý không?

### Câu trả lời

### So sánh với các sản phẩm trong Industry Landscape

Pipeline em xây dựng gồm các thành phần:

* Alert Clustering
* Graph-based RCA
* RAG Retrieval
* LLM Enrichment

Kiến trúc này gần với các nền tảng observability hiện đại có tích hợp AI như:

* Datadog Watchdog
* BigPanda AIOps
* Các nền tảng AIOps kết hợp RCA và Generative AI

Các hệ thống này đều sử dụng topology để khoanh vùng phạm vi ảnh hưởng trước khi dùng AI để giải thích nguyên nhân và đề xuất remediation.

### Đánh giá đối với GeekShop

Theo em, lựa chọn này hoàn toàn phù hợp với đặc thù của GeekShop.

#### 1. Giảm chi phí và số lượng lời gọi LLM

Khi xảy ra sự cố lớn, hệ thống e-commerce có thể tạo ra hàng trăm alert trong thời gian rất ngắn. Nếu gửi trực tiếp toàn bộ alert sang LLM, chi phí và độ trễ sẽ tăng mạnh.

Nhờ bước Alert Clustering, hệ thống có thể gom nhiều alert thành một số lượng nhỏ cluster đại diện. Trong bài lab, hơn 20 alert được nén thành 3 cluster, giúp giảm đáng kể số lần gọi LLM.

#### 2. Service topology tương đối ổn định

GeekShop có service map khá ổn định nên các thuật toán dựa trên topology như PageRank hoặc Graph Traversal phát huy hiệu quả cao. Độ chính xác của RCA tăng lên trong khi chi phí tính toán vẫn thấp.

### Những cải tiến quan trọng em đã thực hiện

1. **Sửa hướng truyền điểm của PageRank**

   Em chuyển từ đồ thị đảo ngược sang đồ thị APM gốc để dòng ảnh hưởng lan truyền đúng theo dependency thực tế.

2. **Bổ sung Topology Diff**

   Chỉ số `in_degree - out_degree` giúp phân biệt service trung gian và service có khả năng là nguồn gốc lỗi, từ đó giảm hiện tượng nhận diện nhầm victim service thành root cause.

3. **Khắc phục Global Timestamp Bug**

   Em chỉ sử dụng timestamp của các alert thuộc cùng cluster khi phân tích trình tự sự kiện, tránh việc các cluster độc lập ảnh hưởng lẫn nhau.

Nhờ các cải tiến trên, pipeline hiện tại phù hợp với bài toán RCA trong môi trường e-commerce có lưu lượng lớn như GeekShop và có thể mở rộng thành một nền tảng AIOps thực tế với chi phí vận hành hợp lý.
