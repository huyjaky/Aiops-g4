# W3-D1 Submission — Phan Đức Huy

## 3 thứ tôi học được
1. **Cơ chế hoạt động của MWMBR (Multi-Window Multi-Burn-Rate):** Hiểu rõ cách kết hợp điều kiện `AND` giữa cửa sổ dài (xác định mức độ nghiêm trọng và lượng budget đã tiêu thụ) và cửa sổ ngắn (kiểm tra xem sự cố còn đang diễn ra hay đã kết thúc). Việc này giúp giảm thiểu báo động giả khi sự cố đã hết mà cửa sổ dài vẫn chưa kịp hồi phục.
2. **Quy đổi ngân sách lỗi (Error Budget):** Cách tính toán từ mục tiêu SLO (như 99.9%) ra tổng lượng request lỗi được phép trong tháng và quy đổi tương đương sang số phút downtime (downtime minutes equivalent) để dễ dàng giao tiếp và thống nhất giữa các phòng ban.
3. **Lựa chọn SLI đúng đắn:** Nhận diện và tránh các anti-pattern phổ biến như sử dụng CPU/Memory làm SLI (chúng chỉ là tín hiệu bão hòa - saturation, không phản ánh trực tiếp trải nghiệm người dùng). Một SLI tốt phải đo lường trực tiếp "nỗi đau" của người dùng như Latency p99 hoặc tỷ lệ lỗi 5xx.

## 1 thứ vẫn chưa rõ
- Cách cấu hình Alertmanager trong thực tế để gom nhóm (grouping), chống trùng lặp (deduplication) và định tuyến (routing) các cảnh báo MWMBR này một cách tối ưu nhất sang các kênh như PagerDuty, Slack, hoặc Jira ticket để tránh gây ngập lụt cảnh báo khi có sự cố diện rộng.

## 1 trade-off trong SLO decision của tôi mà tôi không chắc
- Việc đặt SLO cho DB ở mức **99.95%** (cho phép 22 phút downtime/tháng) khắt khe hơn API là **99.9%** (cho phép 43 phút downtime/tháng). Trên lý thuyết, DB là tầng lõi phục vụ nhiều API nên cần độ tin cậy cao hơn. Tuy nhiên, sự đánh đổi này đòi hỏi hạ tầng DB phải có cơ chế Replication đồng bộ và Auto-failover cực kỳ nhanh nhạy. Nếu xảy ra sự cố DB mất 30 phút để khôi phục, nó sẽ trực tiếp làm DB vi phạm SLO ngay lập tức, trong khi API vẫn có thể nằm trong ngưỡng an toàn của nó, tạo ra sự không đồng nhất về báo cáo độ tin cậy giữa các layer.

## Validation report
- noise_reduction_pct: 86.4%
- mttd_delta_s: 60s
- false_negative: 0
- verdict: pass
