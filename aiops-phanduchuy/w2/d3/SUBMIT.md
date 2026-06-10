# SUBMIT: Reflection & EOD Checkpoint

## 1. Latency budget (p99) và Phase chiếm thời gian nhất
- **Latency Budget (p99):** Mục tiêu thiết kế là dưới **5 giây** khi gọi LLM online, và dưới **200ms** khi chạy ở chế độ offline fallback.
- **Phase chiếm thời gian nhất:** Giai đoạn **Layer 3 (LLM API Call)** chiếm đến **95% - 98%** tổng thời gian phản hồi (khoảng 1 - 3 giây). Điều này là do độ trễ mạng khi gọi API ngoài và thời gian sinh token của LLM. Các thuật toán đồ thị và phân tích logic chạy local chỉ mất khoảng 15 - 50ms.

---

## 2. So sánh xử lý 5 alerts vs 500 alerts (Đặc tính scale)
- **Sự khác biệt:** Khi số lượng alert tăng từ 5 lên 500, thời gian tính toán ở Layer 1 (Correlate) và Layer 2 (Graph RCA) sẽ tăng nhẹ (từ ~10ms lên ~150-200ms) vì số lượng phần tử cần gom cụm và kích thước đồ thị con tăng lên.
- **Quy luật:** Độ trễ **không tăng tuyến tính (linear scale)**. Có một phần **fixed cost** rất lớn (hơn 90% latency) nằm ở cuộc gọi LLM API. Dù đầu vào là 5 hay 500 alerts, danh sách ứng cử viên gửi sang LLM vẫn được giới hạn (tối đa top 5 candidates và top 3 incident history), giúp thời gian xử lý của LLM ổn định. Do đó, hệ thống thể hiện đặc tính có fixed cost cao và tăng chậm khi dữ liệu lớn.

---

## 3. Ứng phó khi LLM provider down giữa buổi demo
- **Cách hoạt động:** File `rca.py` đã bọc toàn bộ LLM call trong khối `try-except`. Khi LLM provider lỗi hoặc timeout:
  1. Hệ thống tự động bắt lỗi và ghi nhận lỗi vào Prometheus metric `aiops_llm_failures_total`.
  2. Hệ thống chuyển sang chế độ **Graph+Retrieval Fallback Mode** (sử dụng độ phân giải từ PageRank kết hợp đối sánh độ tương đồng với lịch sử sự cố `incidents_history.json`).
  3. API vẫn phản hồi thành công với mã **HTTP 200** và trả về Incident Report có độ chính xác cao dựa trên dữ liệu lịch sử và đồ thị, chỉ thay đổi phương thức chuẩn đoán thành `graph+retrieval` hoặc `graph-only-llm-failed`.

---

## 4. Phân biệt `/healthz` và `/readyz`
- **`/healthz` (Liveness Probe):**
  - **Mục đích:** Kiểm tra xem tiến trình FastAPI có đang sống và phản hồi hay không. 
  - **Cách hoạt động:** Chỉ trả về nhanh `{"status": "ok"}` mà không thực hiện kết nối mạng hoặc truy vấn dữ liệu nặng.
  - **Sử dụng:** Kubernetes dùng endpoint này để quyết định có restart (khởi động lại) Pod khi tiến trình bị treo cứng hay không.
- **`/readyz` (Readiness Probe):**
  - **Mục đích:** Kiểm tra xem ứng dụng đã sẵn sàng xử lý request thực tế hay chưa.
  - **Cách hoạt động:** Kiểm tra xem đồ thị topo (`services.json`) và lịch sử sự cố (`incidents_history.json`) đã load vào bộ nhớ thành công chưa, và kiểm tra kết nối tới LLM API.
  - **Sử dụng:** Kubernetes dùng endpoint này để quyết định có chuyển traffic từ load balancer vào Pod hay không (nếu `/readyz` fail, Pod sẽ bị tạm dừng nhận traffic nhưng không bị restart).

---

## 5. Đánh giá khi Trainer POST đồng thời 4 requests từ 4 nhóm
- **Khả năng xử lý:** Endpoint handle ổn định nhờ vào tính năng **Asynchronous (async/await)** của FastAPI và các thư viện hỗ trợ. Trong lúc chờ I/O từ LLM call của request 1, event loop của FastAPI sẽ chuyển qua xử lý CPU/IO cho request 2, 3, 4 một cách mượt mà.
- **Bottleneck đầu tiên:**
  - **Với Online Mode (gọi LLM):** Bottleneck đầu tiên sẽ là **Rate Limit (TPM/RPM)** của OpenAI API key. Nếu vượt quá giới hạn lượt gọi đồng thời từ LLM provider, API sẽ trả về lỗi 429 hoặc bị nghẽn mạng.
  - **Với Offline Mode (fallback):** Bottleneck sẽ là **CPU** của luồng chính khi chạy thuật toán PageRank và gom cụm đồ thị trên NetworkX, do Python bị giới hạn bởi GIL (Global Interpreter Lock) trên 1 tiến trình đơn lẻ. Chúng ta giải quyết điều này ở production bằng cách chạy nhiều worker (`--workers 4` hoặc deploy nhiều replica pods).
