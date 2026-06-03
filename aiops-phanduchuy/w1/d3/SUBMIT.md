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

## Evidence chạy `uv run pipeline.py`
```
uv run pipeline.py
Dataset verified at: ./realKnownCause/machine_temperature_system_failure.csv
Producer: Initializing...
Consumer: Initializing...
Producer: Loaded 22695 rows. Starting to push data to queue...
Consumer: Processed 3000 records... (Latest: Time: 2013-12-13 07:10:00 | Value: 93.54538147 | Mean: 94.46 | Std: 0.84)
Consumer: Processed 6000 records... (Latest: Time: 2013-12-23 17:10:00 | Value: 84.85298264 | Mean: 83.82 | Std: 0.84)
Consumer: Processed 9000 records... (Latest: Time: 2014-01-03 03:10:00 | Value: 86.25383374 | Mean: 86.95 | Std: 0.59)
Consumer: Processed 12000 records... (Latest: Time: 2014-01-13 12:10:00 | Value: 75.32989599999998 | Mean: 77.63 | Std: 2.03)
Consumer: Processed 15000 records... (Latest: Time: 2014-01-23 22:10:00 | Value: 91.67828361 | Mean: 91.85 | Std: 0.85)
Consumer: Processed 18000 records... (Latest: Time: 2014-02-03 08:10:00 | Value: 50.81262286 | Mean: 51.23 | Std: 1.04)
Consumer: Processed 21000 records... (Latest: Time: 2014-02-13 18:10:00 | Value: 94.68288257 | Mean: 97.05 | Std: 1.41)
Producer: Finished pushing all data.
Consumer: Completed processing. Total records: 22695
Consumer: Features successfully saved to: features.parquet
Pipeline completed in 3.51 seconds.
```

## **Tóm tắt** ADR decision (đọc kĩ hơn trong file ADR-001.md)
Hệ thống Payment Microservices cần xử lý khối lượng telemetry rất lớn, khoảng 6 TB log mỗi ngày và 10 triệu sự kiện mỗi giây. Nếu OpenTelemetry Collector ghi trực tiếp dữ liệu vào Elasticsearch và VictoriaMetrics, các hệ thống lưu trữ có thể bị quá tải trong những thời điểm traffic tăng đột biến, dẫn đến backpressure, tăng độ trễ và nguy cơ mất dữ liệu.
Để giải quyết vấn đề này, em quyết định sử dụng Apache Kafka làm lớp trung gian. OTel Collector sẽ gửi toàn bộ metrics, logs và traces vào Kafka, sau đó Apache Flink và các Ingestion Worker sẽ đọc dữ liệu từ Kafka để xử lý và ghi xuống các hệ thống lưu trữ.
Giải pháp này giúp hệ thống hấp thụ các đợt tăng tải lớn, giảm nguy cơ mất dữ liệu, tách biệt các thành phần trong kiến trúc và hỗ trợ nhiều luồng xử lý dữ liệu song song. Tuy nhiên, việc bổ sung Kafka cũng làm tăng chi phí hạ tầng, độ trễ tổng thể của pipeline và yêu cầu nhiều công sức vận hành hơn.
Mặc dù phương án ghi trực tiếp hoặc sử dụng Redis Pub/Sub, RabbitMQ có chi phí thấp hơn, các giải pháp này không đáp ứng tốt yêu cầu về khả năng mở rộng, độ bền dữ liệu và khả năng xử lý lưu lượng cực lớn. Vì vậy, Kafka được lựa chọn như giải pháp cân bằng nhất giữa hiệu năng, độ tin cậy và khả năng mở rộng của hệ thống.

## nếu bạn được hire làm Platform Engineer cho startup 50-service vừa raise Series A, bạn sẽ recommend build hay buy? Tại sao?
Nếu được tuyển làm Platform Engineer cho một startup sở hữu khoảng 50 microservices và vừa hoàn thành vòng gọi vốn Series A, em sẽ ưu tiên lựa chọn **Buy thay vì Build** cho các thành phần nền tảng như observability, monitoring và logging. Lý do là ở giai đoạn này, mục tiêu quan trọng nhất của doanh nghiệp thường là tăng trưởng người dùng, phát triển sản phẩm và đưa tính năng mới ra thị trường nhanh nhất có thể. Việc dành nhiều tháng để tự xây dựng một nền tảng quan sát hệ thống hoàn chỉnh với các thành phần như Kafka, Elasticsearch, VictoriaMetrics, OpenTelemetry hay các mô hình AIOps sẽ tiêu tốn rất nhiều nguồn lực kỹ thuật nhưng chưa tạo ra giá trị trực tiếp cho khách hàng. Trong khi đó, các giải pháp SaaS như Datadog, New Relic hoặc Dynatrace đã cung cấp đầy đủ khả năng monitoring, alerting, tracing và dashboard với độ ổn định cao, giúp đội ngũ kỹ sư tập trung vào việc phát triển sản phẩm thay vì vận hành hạ tầng.
Ngoài ra, chi phí sử dụng dịch vụ SaaS trong giai đoạn đầu thường thấp hơn đáng kể so với chi phí tuyển dụng và duy trì một đội ngũ chuyên trách để xây dựng và vận hành platform nội bộ. Với quy mô khoảng 50 microservices, hệ thống vẫn chưa đủ lớn để biện minh cho việc đầu tư một nền tảng observability tự phát triển. Tuy nhiên, em cũng không cho rằng nên phụ thuộc hoàn toàn vào các giải pháp thương mại trong dài hạn. Khi hệ thống phát triển đến quy mô lớn hơn, lượng telemetry tăng lên mức hàng triệu sự kiện mỗi giây hoặc chi phí SaaS trở nên quá đắt đỏ, em sẽ chuyển dần sang mô hình hybrid và từng bước tự xây dựng các thành phần cốt lõi như Kafka, Flink, VictoriaMetrics hoặc các module AIOps chuyên biệt. Cách tiếp cận này giúp doanh nghiệp cân bằng giữa tốc độ phát triển, chi phí vận hành và khả năng mở rộng trong tương lai.


