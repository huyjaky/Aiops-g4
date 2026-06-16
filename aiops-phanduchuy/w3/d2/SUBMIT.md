# W3-D2 Submission — Phan Duc Huy

## 3 thứ tôi học được về AIOps pipeline của mình
1. **Sự quan trọng của Black-box External Probes**: Tôi học được rằng các metric nội bộ của hệ thống (white-box monitoring) đôi khi có thể báo cáo bình thường ngay cả khi trải nghiệm người dùng cuối đang bị ảnh hưởng nghiêm trọng. Việc duy trì một external probe độc lập để đo lường "steady-state" thực sự (latency & status code dưới góc nhìn của user) là bắt buộc trong Chaos Engineering.
2. **Hạn chế của RCA dựa trên Alert Frequency**: Các mô hình phân tích nguyên nhân gốc rễ (RCA) đơn giản rất dễ bị "đánh lừa" bởi các hiện tượng khuếch đại lỗi như Retry Storms (các tầng downstream gọi liên tiếp tạo ra nhiều alert gây nhiễu). Cần cấu hình luật loại trừ các service đóng vai trò "symptom carrier" (như checkout-svc) để chỉ tập trung vào các service thực sự bị nghẽn (database, payment).
3. **Mối nguy hiểm của Anomaly Noise Floor**: Một bộ detector cấu hình không tốt hoặc có baseline quá rộng (3-sigma trên dữ liệu có phương sai lớn) sẽ hoàn toàn bị mù trước các sự cố âm thầm diễn ra trong thời gian dài (như chậm trễ disk write chậm hoặc log ingestion lag). Việc segment dữ liệu theo khung giờ và sử dụng percentile (p95/p99) thay vì giá trị trung bình là chìa khóa để giảm bớt khoảng trống giám sát này.

## 1 fault mà tôi mong pipeline catch nhưng nó miss
* **Experiment**: `log_collector_disk` (Experiment 7) - disk fill 95% volume.
* **Why I expected detection**: Ổ đĩa của log-collector đầy đến 95% trực tiếp ảnh hưởng đến khả năng lưu trữ log và làm tăng log ingestion lag lên gấp nhiều lần. Tôi kỳ vọng rằng pipeline detector phải ngay lập tức bắn cảnh báo lag khi vượt qua ngưỡng thông thường để tránh mất mát log hệ thống.
* **Why pipeline missed (hypothesis)**: Detector sử dụng thuật toán tính toán ngưỡng động dựa trên mean và standard deviation của 120s trước đó. Do log ingestion lag là metric có độ biến động rất lớn (high variance), standard deviation lớn dẫn đến việc ngưỡng phát hiện (noise floor) bị nâng lên quá cao. Độ trễ 120s sinh ra từ sự cố disk fill bị chìm nghỉm dưới noise floor này và không được kích hoạt alert.

## 1 trade-off trong design pipeline mà tôi muốn rethink
* **Vấn đề**: Sự cân bằng giữa **Alert Storm Suppression (Giảm nhiễu Alert)** và **Root-Cause Coverage (Phát hiện triệt để nguyên nhân)**.
* **Chi tiết**: Để tránh làm ngập lụt kênh chat của đội trực vận hành, pipeline của tôi gom cụm các alert rất tích cực dựa trên thời gian và khoảng cách topology mạng. Tuy nhiên, điều này dẫn đến một trade-off lớn (được chỉ ra ở Experiment 5): khi Database Connection Pool bị cạn kiệt, pipeline gom cả alert của Database và alert lỗi kết nối của `payment-svc` vào cùng một incident. Vì `payment-svc` có tần suất lỗi cao hơn và nằm ở tầng dịch vụ người dùng, hệ thống RCA tự động chỉ định `payment-svc` làm Root Cause, gián tiếp bỏ qua thủ phạm thực sự ở tầng Database (`payment-db`).
* **Rethink**: Tôi muốn cấu hình lại công cụ tương quan (correlator) để không chỉ gom nhóm theo thời gian và sự liên kết đơn thuần, mà cần áp dụng **Direct Causal Graph (Đồ thị nhân quả có hướng)** dựa trên log error stack-traces hoặc phân tích trễ tín hiệu (lag correlation) để xác định chính xác dòng chảy của lỗi từ dưới lên.

## Scoreboard summary
* **detected**: 9/10 (90.0% recall)
* **rca_correct**: 8/9 (88.9% accuracy)
* **mttd_p50**: 1s
* **false_alarms**: 0
* **verdict**: PASS (Vượt qua yêu cầu Acceptance: Detected >= 70%, RCA correct >= 70% trên số detected, False alarms <= 1)
