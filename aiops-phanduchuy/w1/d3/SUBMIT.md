## Screenshot architecture diagram
<img width="4411" height="7115" alt="g4-w1-d3-2026-06-03-021658" src="https://github.com/user-attachments/assets/715600e6-319f-406f-a5f5-eceb58fa460c" />

## Bảng cost estimate (copy từ output cost_model.py)
```bash
py cost_model.py
============================================================
Tier: Small (10 Services, 50 GB Log/day, 100,000 EPS Metric)
------------------------------------------------------------
Category             | Build (In-house OSS) | Buy (Datadog SaaS)
------------------------------------------------------------
Compute / APM        | $675.00              | $1,200.00
Storage / Logs       | $99.14               | $2,250.00
Network / Metrics    | $39.66               | $5,000.00
Ops Overhead         | $5,000.00            | $1,000.00
------------------------------------------------------------
TOTAL MONTHLY COST   | $5,813.80            | $9,450.00

Conclusion: SaaS is 1.6x the cost of Build.
Building in-house saves $3,636.20 per month.
============================================================

============================================================
Tier: Medium (100 Services, 500 GB Log/day, 1,000,000 EPS Metric)
------------------------------------------------------------
Category             | Build (In-house OSS) | Buy (Datadog SaaS)
------------------------------------------------------------
Compute / APM        | $6,750.00            | $12,000.00
Storage / Logs       | $991.40              | $22,500.00
Network / Metrics    | $396.56              | $50,000.00
Ops Overhead         | $15,000.00           | $3,000.00
------------------------------------------------------------
TOTAL MONTHLY COST   | $23,137.96           | $87,500.00

Conclusion: SaaS is 3.8x the cost of Build.
Building in-house saves $64,362.04 per month.
============================================================

============================================================
Tier: Large (1000 Services, 5000 GB Log/day, 10,000,000 EPS Metric)
------------------------------------------------------------
Category             | Build (In-house OSS) | Buy (Datadog SaaS)
------------------------------------------------------------
Compute / APM        | $67,500.00           | $120,000.00
Storage / Logs       | $9,913.99            | $225,000.00
Network / Metrics    | $3,965.60            | $500,000.00
Ops Overhead         | $40,000.00           | $5,000.00
------------------------------------------------------------
TOTAL MONTHLY COST   | $121,379.58          | $850,000.00

Conclusion: SaaS is 7.0x the cost of Build.
Building in-house saves $728,620.42 per month.
============================================================
```

## **Tóm tắt** ADR decision (đọc kĩ hơn trong file ADR-001.md)
Hệ thống Payment Microservices cần xử lý khối lượng telemetry rất lớn, khoảng 6 TB log mỗi ngày và 10 triệu sự kiện mỗi giây. Nếu OpenTelemetry Collector ghi trực tiếp dữ liệu vào Elasticsearch và VictoriaMetrics, các hệ thống lưu trữ có thể bị quá tải trong những thời điểm traffic tăng đột biến, dẫn đến backpressure, tăng độ trễ và nguy cơ mất dữ liệu.
Để giải quyết vấn đề này, em quyết định sử dụng Apache Kafka làm lớp trung gian. OTel Collector sẽ gửi toàn bộ metrics, logs và traces vào Kafka, sau đó Apache Flink và các Ingestion Worker sẽ đọc dữ liệu từ Kafka để xử lý và ghi xuống các hệ thống lưu trữ.
Giải pháp này giúp hệ thống hấp thụ các đợt tăng tải lớn, giảm nguy cơ mất dữ liệu, tách biệt các thành phần trong kiến trúc và hỗ trợ nhiều luồng xử lý dữ liệu song song. Tuy nhiên, việc bổ sung Kafka cũng làm tăng chi phí hạ tầng, độ trễ tổng thể của pipeline và yêu cầu nhiều công sức vận hành hơn.
Mặc dù phương án ghi trực tiếp hoặc sử dụng Redis Pub/Sub, RabbitMQ có chi phí thấp hơn, các giải pháp này không đáp ứng tốt yêu cầu về khả năng mở rộng, độ bền dữ liệu và khả năng xử lý lưu lượng cực lớn. Vì vậy, Kafka được lựa chọn như giải pháp cân bằng nhất giữa hiệu năng, độ tin cậy và khả năng mở rộng của hệ thống.

## nếu bạn được hire làm Platform Engineer cho startup 50-service vừa raise Series A, bạn sẽ recommend build hay buy? Tại sao?
Nếu được tuyển làm Platform Engineer cho một startup có khoảng 50 microservices vừa gọi vốn Series A, em sẽ ưu tiên lựa chọn **Buy thay vì Build**. Ở giai đoạn này, mục tiêu quan trọng nhất là phát triển sản phẩm và tăng trưởng nhanh, nên việc sử dụng các nền tảng observability đã hoàn thiện như Datadog hoặc New Relic sẽ giúp tiết kiệm thời gian, giảm rủi ro vận hành và cho phép đội ngũ tập trung vào business value. Em chỉ cân nhắc tự xây dựng platform khi quy mô hệ thống và chi phí SaaS đã đủ lớn hoặc khi doanh nghiệp cần các năng lực AIOps đặc thù để tạo lợi thế cạnh tranh.

