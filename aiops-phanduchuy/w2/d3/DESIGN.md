# BẢN THIẾT KẾ: API Phục vụ Sự cố AIOps (AIOps Incident Serving API)

## 1. Kiến trúc Pipeline trong Endpoint

Endpoint phục vụ chính (`POST /incident`) triển khai một pipeline tuần tự gồm 3 lớp để xử lý hàng loạt cảnh báo (alerts):
- **Lớp 1 (Gom cụm / Correlation):** Các cảnh báo được nhóm theo trình tự thời gian bằng cách sử dụng một cửa sổ trượt thời gian (`gap_sec=120s`) để tách biệt các đợt bão cảnh báo khác nhau. Trong mỗi cửa sổ thời gian đó, các cảnh báo được gom cụm theo cấu trúc đồ thị topo (dựa trên đồ thị phụ thuộc dịch vụ) với giới hạn khoảng cách bước nhảy tối đa (`max_hop=2`). Em chọn `gap_sec=120s` vì các cảnh báo SRE trong hệ thống microservices thực tế thường lan truyền trong vòng 2 phút kể từ khi sự cố gốc xảy ra, và `max_hop=2` giúp tránh gom cụm các phân đoạn mạng không liên quan.
- **Lớp 2 (Tìm nguyên nhân gốc bằng Đồ thị / Graph RCA):** Đối với cụm cảnh báo chính (cụm lớn nhất), em áp dụng một công thức heuristic kết hợp: Thuật toán PageRank trên đồ thị con để phân tích luồng lỗi lan truyền, hiệu số giữa bậc vào (in-degree) và bậc ra (out-degree) để kiểm tra điểm nguồn topo, mốc thời gian cảnh báo sớm nhất (lan truyền theo thời gian) và mức độ nghiêm trọng (severity).
- **Lớp 3 (Làm giàu thông tin bằng LLM / LLM Enrichment):** Các ứng cử viên hàng đầu và ngữ cảnh đồ thị phụ thuộc được đưa vào LLM (OpenAI `gpt-4o-mini`) thông qua lớp truy xuất RAG chứa top-k các sự cố lịch sử tương tự nhằm xác định chính xác dịch vụ gây lỗi gốc, phân loại nhóm lỗi (class) và đưa ra các hành động khắc phục cụ thể.

---

## 2. Phân rã Ngân sách Độ trễ - Latency Budget (Mục tiêu: p99 < 5s)

| Giai đoạn (Phase) | Thời gian chạy (ms) | % Ngân sách | Giải thích chi tiết |
|---|---|---|---|
| Phân tích & Validate Request | 5 - 15 | ~0.3% | Khởi tạo và kiểm tra schema của Alert bằng Pydantic |
| L1 Gom cụm (Vòng lặp Python) | 20 - 50 | ~1.0% | Chia cửa sổ trượt và duyệt đồ thị bằng NetworkX |
| L2 RCA Đồ thị | 10 - 30 | ~0.6% | Tính toán PageRank và sắp xếp điểm số đồ thị con |
| L3 Gọi LLM (Outbound API) | 800 - 3000 | ~98.0% | Gọi API mạng bên ngoài & thời gian sinh token của LLM |
| Serialization Phản hồi | 5 - 10 | ~0.1% | Chuyển đổi dữ liệu sang chuỗi JSON khớp schema IncidentResponse |
| **Tổng cộng** | **840 - 3105** | **100%** | **Nằm trong ngân sách thiết kế p99 < 5s** |

---

## 3. Các vấn đề trong môi trường Production (Khả năng chịu lỗi)

Mối quan tâm hàng đầu của em là **Tính sẵn sàng của dịch vụ LLM bên ngoài (LLM Down/Timeout)**. 
- **Chiến lược khắc phục:** Nếu thiếu khóa API OpenAI, hoặc cuộc gọi API bị lỗi/quá thời gian phản hồi, máy chủ của em sẽ bắt ngoại lệ này và tự động chuyển sang chế độ dự phòng **Graph+Retrieval Mode**. Em sẽ lấy các ứng cử viên hàng đầu trực tiếp từ đồ thị topo, truy vấn lịch sử sự cố bằng thuật toán đối sánh độ tương đồng `top_k_similar`, ghi đè lỗi gốc nếu phát hiện sự cố tương tự có độ trùng khớp cao ($\ge 0.8$) và trả về một báo cáo chuẩn đoán chất lượng tốt mà không cần gọi LLM. Điều này giúp ngăn chặn việc gián đoạn API ngoài làm treo luồng cảnh báo SRE quan trọng.

---

## 4. Đánh giá Trade-offs: Tại sao em chọn FastAPI thay vì Flask hay BentoML?

- **FastAPI (Lựa chọn của em):** Được chọn vì hỗ trợ cú pháp bất đồng bộ (async/await) nguyên bản, cho phép xử lý đồng thời không nghẽn luồng (non-blocking concurrency) trong lúc chờ các cuộc gọi API LLM tốn thời gian. Thêm vào đó, việc tự động sinh tài liệu Swagger/OpenAPI và cơ chế validate của Pydantic giúp đảm bảo các dữ liệu đầu vào không hợp lệ sẽ bị trả lỗi `422 Unprocessable Entity` ngay lập tức thay vì gây lỗi sập hệ thống `500 Internal Server Error`.
- **Flask:** Hoạt động theo cơ chế đồng bộ (synchronous). Để xử lý đồng thời nhiều cuộc gọi API LLM tốn thời gian, Flask yêu cầu cấu hình thêm các thư viện custom phức tạp như greenlet hoặc threadpool, đồng thời thiếu tính năng validate dữ liệu đầu vào nguyên bản.
- **BentoML:** Rất tối ưu cho việc đóng gói và host các mô hình Học máy lớn (quản lý model store, micro-batching). Tuy nhiên, nó mang lại độ phức tạp quá mức cần thiết, đường cong học tập dốc và overhead tài nguyên không đáng có đối với một pipeline tập trung vào siêu dữ liệu (metadata-centric) như dự án của em.
