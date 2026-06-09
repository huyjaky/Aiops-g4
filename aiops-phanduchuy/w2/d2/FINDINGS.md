## Câu hỏi 1: Đối với cluster chính, root cause là gì và vì sao?

### Tóm tắt cụm sự cố chính (c-000-000)

* **Thời gian diễn ra:** Từ `2026-06-12T09:42:01Z` đến `2026-06-12T09:46:01Z`
* **Số lượng alerts:** 15 alerts
* **Các service liên quan:** `checkout-svc`, `edge-lb`, `payment-svc`, `cart-svc`, `notification-svc`, `recommender-svc`

### Kết quả phân tích và lý do xác thực

* **Root Cause:** `payment-svc`
* **Phân loại:** `connection_pool_exhaustion`
* **Confidence:** `0.97`

#### Lý do

1. **Phân tích Alert Timeline**

   Em nhận thấy sự cố xuất hiện đầu tiên tại `payment-svc` vào lúc `09:42:01` với cảnh báo sử dụng connection pool đạt 85%. Chỉ sau đó vài giây, tỷ lệ sử dụng pool tăng lên 99%, kéo theo P99 latency tăng lên `1840ms` và phát sinh cảnh báo `error_rate`.

   Trong khi đó, `checkout-svc` chỉ bắt đầu xuất hiện cảnh báo từ `09:42:45` và báo lỗi downstream payment tại `09:43:01`. Điều này cho thấy các lỗi tại `checkout-svc` là hậu quả của sự cố xảy ra ở `payment-svc`, không phải nguyên nhân gốc.

2. **Phân tích bằng Graph + Topology Diff + Severity**

   Em sử dụng PageRank trên đồ thị APM gốc để giữ nguyên hướng phụ thuộc giữa các service. Đồng thời, em kết hợp thêm chỉ số `Topology Diff (in_degree - out_degree)` để phân biệt service trung gian với service có khả năng là nguồn phát sinh lỗi.

   Kết quả cho thấy `payment-svc` có `in-degree = 1`, `out-degree = 0` và đạt điểm đồ thị cao nhất (`0.9648`), trong khi `checkout-svc` chỉ đóng vai trò trung chuyển. Ngoài ra, em cũng sửa lỗi Global Timestamp Bug bằng cách chỉ phân tích các alert thuộc riêng cluster `c-000-000`.

3. **Đối chiếu với dữ liệu lịch sử (RAG)**

   Hệ thống truy xuất được incident tương đồng nhất là `INC-2025-11-08`, liên quan đến lỗi rò rỉ connection pool tại `payment-svc`. Kết quả truy xuất hoàn toàn trùng khớp với kết quả phân tích đồ thị, giúp em xác định `payment-svc` là root cause với độ tin cậy rất cao.

---

## Câu hỏi 2: Với confidence hiện tại, em có dám triển khai auto-remediation không?

### Kết quả phân tích

* **Confidence:** `0.97`
* **Quyết định:** Em tự tin triển khai auto-remediation.

### Hành động đề xuất

* Auto-rollback phiên bản triển khai gần nhất của `payment-svc`.
* Hoặc tự động scale/restart connection pool liên quan đến database.

### Lý do

Điểm confidence đạt `0.97` và tất cả nguồn bằng chứng từ Alert Timeline, Graph Analysis, Severity Score và RAG đều chỉ về cùng một root cause là `payment-svc`.

Bên cạnh đó, thuật toán đồ thị cải tiến giúp giảm đáng kể nguy cơ rollback nhầm các service bị ảnh hưởng như `checkout-svc` hoặc `edge-lb`. Vì vậy, việc thực hiện remediation trực tiếp trên `payment-svc` có khả năng khôi phục hệ thống nhanh chóng và giảm MTTR.

Tuy nhiên, trong môi trường production thực tế, em vẫn ưu tiên triển khai auto-remediation thông qua các guardrail hoặc cơ chế approval để hạn chế rủi ro từ các trường hợp phân loại sai hiếm gặp.

---

## Câu hỏi 3: Một trường hợp em chưa hoàn toàn chắc chắn và lý do

### Trường hợp

Cluster `c-001-000` gồm hai service `checkout-svc` và `search-svc`, xuất hiện trong khoảng thời gian từ `09:46:50` đến `09:47:12`.

### Lý do

Mặc dù hệ thống xếp hạng `checkout-svc` cao hơn (`0.70` so với `0.50`) nhờ xuất hiện cảnh báo mức `crit`, em vẫn chưa hoàn toàn chắc chắn về vai trò của `search-svc` trong cụm này.

Nguyên nhân là do hai service không có quan hệ phụ thuộc trực tiếp trong topology. Alert liên quan đến truy vấn database chậm của `search-svc` có thể chỉ là một sự kiện nền độc lập xảy ra cùng thời điểm. Việc gom cụm dựa trên cửa sổ thời gian có khả năng tạo nhiễu trong quá trình điều tra và khiến SRE tập trung sai hướng thay vì xử lý lỗi `deadlock` tại `checkout-svc`.

---

## Câu hỏi bổ sung: Em có thực hiện Bonus 3 (LLM Enrichment) không? So sánh kết quả giữa LLM và kNN Top-1, đồng thời rút ra nhận xét từ bài viết *Building Effective Agents*.

### Trả lời

Em **đã thực hiện Bonus 3 – LLM Enrichment**.

### So sánh kết quả giữa LLM và kNN Top-1

| Cluster   | LLM Class                  | kNN Top-1 Class            | Kết quả |
| --------- | -------------------------- | -------------------------- | ------- |
| c-000-000 | connection_pool_exhaustion | connection_pool_exhaustion | Khớp    |
| c-001-000 | deadlock                   | deadlock                   | Khớp    |
| c-002-000 | connection_pool_exhaustion | connection_pool_exhaustion | Khớp    |

Kết quả cho thấy tất cả các cluster đều có sự đồng nhất hoàn toàn giữa dự đoán của LLM và incident lịch sử được truy xuất từ RAG. Điều này cho thấy dữ liệu retrieval đã cung cấp ngữ cảnh đủ mạnh để hỗ trợ LLM đưa ra kết luận chính xác và hạn chế hiện tượng hallucination.

