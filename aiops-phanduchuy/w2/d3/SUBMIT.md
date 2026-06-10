# BÀN GIAO: Báo cáo Thử nghiệm & Câu hỏi Thu hoạch EOD

## Câu hỏi 1: Latency budget của endpoint bạn là bao nhiêu (p99)? Phase nào chiếm thời gian nhất?

### Trả lời:
- **Ngân sách độ trễ (Latency Budget p99):** Mục tiêu thiết kế cho endpoint `/incident` của em là dưới **5 giây** khi chạy ở chế độ Online (gọi LLM) và dưới **200ms** khi chạy ở chế độ Offline (không dùng LLM).
- **Phase chiếm thời gian nhất:** Giai đoạn **Layer 3 (LLM API Call)** chiếm đến **95% - 98%** tổng thời gian phản hồi (dao động từ 1 - 3 giây). Nguyên nhân là do đây là cuộc gọi mạng I/O-bound ra ngoài internet và phụ thuộc trực tiếp vào tốc độ sinh token của LLM. Các giai đoạn tính toán thuật toán đồ thị cục bộ (Local Graph) của em chỉ chiếm khoảng 15 - 50ms (dưới 5%).

---

## Câu hỏi 2: Endpoint của bạn xử lý 1 input với 5 alert vs 500 alert — sự khác biệt latency là gì? Linear scale? Hay có phần fixed cost?

### Trả lời:
- **Sự khác biệt về độ trễ:** 
  - Khi tăng lượng cảnh báo đầu vào từ 5 lên 500, thời gian thực thi của Layer 1 (Gom cụm) và Layer 2 (RCA đồ thị) của em sẽ tăng nhẹ (từ ~10ms lên khoảng ~150-200ms) do NetworkX phải duyệt và tính toán PageRank trên một tập đồ thị con lớn hơn.
  - Tuy nhiên, độ trễ tổng thể của API **không tăng tuyến tính (linear scale)**. 
- **Đặc tính Fixed Cost:**
  - Hệ thống của em chịu ảnh hưởng bởi một khoản **chi phí cố định (fixed cost)** rất lớn từ cuộc gọi LLM API ở Layer 3. Vì danh sách ứng cử viên gửi đi LLM luôn được em giới hạn (tối đa top 5 dịch vụ lỗi và top 3 incident lịch sử), thời gian xử lý của LLM gần như giữ nguyên cho dù dữ liệu thô ban đầu có là 5 hay 500 alert. Do đó, hệ thống thể hiện đặc tính tăng trưởng chậm (sub-linear) nhờ vào chi phí cố định lớn của LLM.

---

## Câu hỏi 3: LLM provider down giữa demo. Hệ thống bạn behave thế nào? Phương án dự phòng?

### Trả lời:
- **Cách thức hoạt động của hệ thống:**
  - Toàn bộ hàm gọi LLM (`call_llm_rca` trong `rca.py`) được em bao bọc chặt chẽ trong khối lệnh `try-except`.
  - Nếu nhà cung cấp dịch vụ LLM bị sập hoặc trả về lỗi, hệ thống của em sẽ tự động bắt ngoại lệ này, tăng giá trị của Prometheus metric `aiops_llm_failures_total` để cảnh báo hệ thống giám sát.
- **Phương án dự phòng (Fallback):**
  - Hệ thống của em ngay lập tức chuyển sang chế độ **Graph+Retrieval Fallback Mode**. 
  - Tại đây, hệ thống sử dụng kết quả thuật toán PageRank trên đồ thị để tìm ra dịch vụ có điểm số cao nhất, kết hợp đối sánh độ tương đồng RAG với cơ sở dữ liệu lịch sử sự cố (`incidents_history.json`).
  - Kết quả API trả về vẫn là **HTTP 200** với chẩn đoán sự cố đầy đủ và phương thức RCA được ghi nhận là `graph-only-llm-failed` hoặc `graph+retrieval` thay vì trả lỗi HTTP 500 gây sập hệ thống.

---

## Câu hỏi 4: /healthz và /readyz khác nhau gì? Khi nào dùng cái nào?

### Trả lời:
- **Endpoint `/healthz` (Liveness Probe - Kiểm tra sự sống):**
  - **Mục đích:** Xác minh xem tiến trình ứng dụng FastAPI/Uvicorn của em có đang chạy bình thường hay bị treo cứng (deadlock).
  - **Đặc điểm:** Chỉ trả về nhanh `{"status": "ok"}` mà không thực hiện kết nối mạng hoặc truy vấn dữ liệu nặng để tránh tạo tải giả.
  - **Khi nào dùng:** Kubernetes dùng nó để tự động khởi động lại (restart) container của em nếu endpoint này ngừng phản hồi.
- **Endpoint `/readyz` (Readiness Probe - Kiểm tra độ sẵn sàng):**
  - **Mục đích:** Xác minh xem ứng dụng của em đã sẵn sàng nhận và xử lý traffic thực tế từ người dùng hay chưa.
  - **Đặc điểm:** Thực hiện kiểm tra trạng thái nạp dữ liệu đồ thị topo (`services.json`), cơ sở dữ liệu incidents lịch sử, và kiểm tra kết nối mạng tới LLM (nếu bật cờ sử dụng LLM).
  - **Khi nào dùng:** Kubernetes dùng nó để quyết định có đưa container của em vào cụm Load Balancer hay không. Nếu `/readyz` trả lỗi (ví dụ: HTTP 503), Kubernetes sẽ tạm thời ngắt container khỏi luồng traffic nhưng không restart nó.

---

## Câu hỏi 5: Trainer POST 4 request đồng thời từ 4 nhóm khác nhau. Endpoint bạn handle ổn không? Bottleneck đầu tiên?

### Trả lời:
- **Khả năng xử lý của hệ thống:**
  - Endpoint của em hoạt động **rất ổn định** dưới 4 request đồng thời nhờ vào kiến trúc không đồng bộ **Async/Await** của FastAPI. Khi request 1 đang đợi phản hồi I/O từ LLM API, Event Loop của FastAPI sẽ ngay lập tức nhường quyền kiểm soát để xử lý CPU hoặc gọi I/O cho request 2, 3, 4.
- **Điểm nghẽn (Bottleneck) đầu tiên:**
  - **Chế độ Online (sử dụng LLM):** Điểm nghẽn đầu tiên sẽ là **Rate Limit (TPM - Token Per Minute / RPM - Request Per Minute)** của tài khoản API LLM. Nếu vượt ngưỡng này, LLM provider sẽ trả về lỗi `429 Too Many Requests`.
  - **Chế độ Offline (fallback không LLM):** Điểm nghẽn sẽ là **CPU** của luồng chính khi chạy thuật toán PageRank và gom cụm đồ thị trên NetworkX, do Python bị giới hạn bởi GIL (Global Interpreter Lock). Cách giải quyết trên Production của em là triển khai nhiều worker thông qua Uvicorn (`--workers 4`) hoặc nhân bản thêm Pods trên Kubernetes.
