# Detection Approach — DESIGN.md

## Approach em dùng
Sử dụng Moving Window Average (Trung bình trượt) kết hợp với Static Thresholds (Ngưỡng tĩnh) cho các metrics đặc trưng.

## Tại sao chọn approach này
Approach này rất phù hợp với streaming data vì:
1. Độ trễ (latency) cực thấp, không cần lưu trữ nhiều dữ liệu lịch sử (chỉ cần vài data points gần nhất).
2. Moving Window Average giúp làm mượt (smooth) các nhiễu ngẫu nhiên (noise) của dữ liệu, giảm thiểu cảnh báo giả (false positives) so với việc chỉ kiểm tra từng data point đơn lẻ.
3. Các dạng lỗi (faults) trong bài toán này có biểu hiện rất rõ ràng trên các metrics cụ thể, nên dùng ngưỡng tĩnh dựa trên normal ranges đã cho là đủ chính xác và nhanh gọn.

## Cách hoạt động
Pipeline duy trì một hàng đợi (queue) chứa tối đa 5 payload gần nhất. Mỗi khi có payload mới:
1. Lưu metric vào hàng đợi.
2. Nếu hàng đợi có ít nhất 3 phần tử, tính trung bình của `upstream_timeout_rate`, `http_requests_per_sec`, và `memory_usage_bytes` của các phần tử trong hàng đợi.
3. So sánh các giá trị trung bình này với các ngưỡng bất thường đã được xác định.
4. Ghi log cảnh báo đầu tiên cho một loại lỗi vào file `alerts.jsonl` và chặn không ghi đè lại cùng loại lỗi đó để tránh spam cảnh báo.

## Parameters tôi chọn
- **Window size**: `5` (lưu trữ 5 points), nhưng chỉ cần >= 3 points là bắt đầu check. Kích thước này đủ để lọc nhiễu mà không làm chậm việc phát hiện (delay tối đa chỉ khoảng vài giây).
- **Threshold `dependency_timeout`**: `upstream_timeout_rate > 3.0%`. (Bình thường <= 0.4%). Khi có lỗi, rate này tăng rất nhanh lên mức cao.
- **Threshold `traffic_spike`**: `http_requests_per_sec > 250`. (Bình thường dao động 80-160, tính cả nhiễu và peak thì hiếm khi qua 200). 
- **Threshold `memory_leak`**: `memory_usage_bytes > 1.05 GB (1,050,000,000 bytes)`. (Bình thường xoay quanh 800 MB, tối đa khoảng 860 MB bao gồm nhiễu). Khi RAM tăng đều đặn vượt 1.05 GB, chắc chắn là có memory leak.

## Cải thiện nếu có thêm thời gian
1. Thay vì sử dụng ngưỡng tĩnh, có thể áp dụng Exponential Moving Average (EMA) kết hợp với Z-Score để tự động điều chỉnh dải an toàn, từ đó phát hiện các thay đổi từ từ tốt hơn.
2. Có thể phân tích thêm phần `logs` để củng cố độ tin cậy (ví dụ kết hợp rate limit + log "Server overloaded").
3. Thêm rate-limiting cho việc alert thay vì chỉ chặn hoàn toàn bằng `alerted_types` set (ví dụ chỉ alert 1 lần mỗi 15 phút cho cùng một loại lỗi).
