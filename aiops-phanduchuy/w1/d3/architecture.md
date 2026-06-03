# E2E Data Layer Architecture

**Use case:** Anomaly Detection trên Payment Service

```mermaid
graph TD
    %% Style Definitions
    classDef service fill:#d4edda,stroke:#28a745,stroke-width:2px;
    classDef collection fill:#cce5ff,stroke:#007bff,stroke-width:2px;
    classDef transport fill:#fff3cd,stroke:#ffc107,stroke-width:2px;
    classDef process fill:#f8d7da,stroke:#dc3545,stroke-width:2px;
    classDef storage fill:#e2e3e5,stroke:#6c757d,stroke-width:2px;
    classDef query fill:#d1ecf1,stroke:#17a2b8,stroke-width:2px;

    subgraph "AIOps E2E Data Layer"
        direction TB
        
        %% 1. Service Layer
        subgraph "1. Service"
            P1(Payment Gateway API):::service
            P2(Transaction Engine):::service
        end
        
        %% 2. Collection
        subgraph "2. Collection"
            OTel[OpenTelemetry Collector]:::collection
        end
        
        %% 3. Transport
        subgraph "3. Transport"
            Kafka[Apache Kafka Cluster]:::transport
        end
        
        %% 4. Processing
        subgraph "4. Processing"
            Flink[Apache Flink - Stream Processing]:::process
        end
        
        %% 5. Storage
        subgraph "5. Storage"
            VM[(VictoriaMetrics / Prometheus)]:::storage
            ES[(Elasticsearch / OpenSearch)]:::storage
        end
        
        %% 6. Query & ML
        subgraph "6. Query/ML"
            Grafana[Grafana - Dashboards & Alerts]:::query
            ML[Python AI Services - Anomaly Detector]:::query
        end
        
        %% Connections
        P1 -- "OTel SDK (Metrics/Traces)" --> OTel
        P2 -- "OTel SDK (Metrics/Traces)" --> OTel
        
        OTel -- "Publish Telemetry Stream" --> Kafka
        
        Kafka -- "Consume Raw Data" --> Flink
        
        Flink -- "Aggregated Metrics/Features" --> VM
        Flink -- "Enriched Traces/Logs" --> ES
        
        VM -- "Time-series Queries" --> Grafana
        ES -- "Log/Trace Search" --> Grafana
        
        VM -- "Historical & Real-time Data" --> ML
        ML -- "Anomaly Scores & Alerts" --> Kafka
    end
```

### Chi tiết các Tools được lựa chọn:
1. **Service**: Các Microservices về thanh toán (Ví dụ được build bằng Spring Boot hoặc Golang).
2. **Collection**: **OpenTelemetry (OTel) Collector** (Thu thập metrics tỷ lệ lỗi thanh toán, độ trễ và traces).
3. **Transport**: **Apache Kafka** (Làm message broker trung tâm chịu tải cao, buffer dữ liệu chống nghẽn).
4. **Processing**: **Apache Flink** (Xử lý stream thời gian thực, rolling windows để tính tỉ lệ lỗi, extract các time-series features cho ML).
5. **Storage**: 
    - **VictoriaMetrics** (Lưu trữ Time-series metrics do Flink tính toán/đẩy ra).
    - **Elasticsearch** (Lưu các logs và raw traces lỗi để truy xuất khi có cảnh báo).
6. **Query/ML**: 
    - **Grafana** (Visualization hệ thống payment, truy xuất metrics và logs, hiển thị cảnh báo).
    - **Python AI Services / MLflow** (Triển khai mô hình Machine Learning như Isolation Forest, LSTM để phát hiện Anomaly. Mô hình lấy dữ liệu metrics từ VictoriaMetrics và đẩy ngược cảnh báo nếu phát hiện bất thường thanh toán về Kafka).
