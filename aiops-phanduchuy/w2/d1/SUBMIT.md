# Báo cáo bài làm Lab W2-D1: Alert Correlation

## 1. Lựa chọn tham số thiết kế

### Lựa chọn `gap_sec`
* **Giá trị em chọn**: `120` (giây)
* **Lý do**: Đây là khoảng thời gian (`sweet spot`) lý tưởng để gom các alert của cùng một sự cố lan truyền (`cascade`). Thực nghiệm `grid search` của em trên bộ dữ liệu mẫu `alerts_sample.jsonl` cho thấy với `gap_sec = 120`, toàn bộ 20 alerts được gom vào 1 `session` duy nhất trước khi phân tích `topology`, đảm bảo không bị bỏ sót chuỗi `cascade`.

### Lựa chọn `max_hop`
* **Giá trị em chọn**: `1` hoặc `2` (Tùy thuộc vào chiến lược giảm tiếng ồn)
* **Lý do**: 
  * Với `max_hop = 2`, toàn bộ 20 alerts gom về **1 cụm duy nhất** (Tỷ lệ giảm nhiễu `reduction ratio` = 95%). Lựa chọn này an toàn để bắt hết các `symptoms` lan truyền xa nhưng có điểm yếu là gom nhầm alert không liên quan của `recommender-svc`.
  * Với `max_hop = 1`, em thu được **2 cụm**: Cụm sự cố chính (19 alerts) và cụm cô lập của `recommender-svc` (1 alert). Điều này giúp cô lập chính xác alert nhiễu độc lập của recommender.

---

## 2. Các Design Trade-offs Quan Trọng

Trong quá trình thiết kế hệ thống Alert Correlation này, em đã phân tích và cân nhắc các `trade-offs` lớn sau:

### Trade-off 1: Độ nhạy thời gian của Session (`gap_sec`)
* **Lựa chọn**: `gap_sec = 120s`.
* **Phân tích trade-off**:
  * **Thiên vị Tách biệt (Nhỏ - e.g., 30s)**: Hệ thống sẽ tối ưu hóa để phân tách các sự cố xảy ra liên tiếp nhanh. Tuy nhiên, nó sẽ làm phân mảnh một sự cố lớn kéo dài thành nhiều cụm nhỏ rời rạc (tăng tỷ lệ `false negative` trong việc gom cụm triệu chứng liên đới).
  * **Thiên vị Gom cụm (Lớn - e.g., 600s)**: Hệ thống sẽ đảm bảo không bỏ sót bất kỳ triệu chứng lan truyền chậm nào. Nhưng nó sẽ gộp nhầm các sự cố hoàn toàn độc lập xảy ra gần nhau về mặt thời gian (tăng tỷ lệ `false positive` trong việc tương quan).
  * **Quyết định**: `120s` là điểm cân bằng giữa hai thái cực trên cho hầu hết các hệ thống production.

### Trade-off 2: Phạm vi ảnh hưởng trên Topology Graph (`max_hop`)
* **Lựa chọn**: `max_hop = 1` hoặc `2`.
* **Phân tích trade-off**:
  * **`max_hop = 2` (Ưu tiên độ phủ - Coverage)**: Chấp nhận tăng tỷ lệ `false positive` để đảm bảo bắt trọn gói toàn bộ chuỗi lỗi lan truyền qua nhiều tầng dịch vụ (ví dụ từ `payment-svc` nghẽn DB dẫn đến lỗi checkout ở `checkout-svc` và lỗi 5xx ở `edge-lb`). Nhược điểm là dễ gom nhầm các dịch vụ phụ cận có alert trùng giờ nhưng không liên quan (như `recommender-svc` bị lỗi do `batch retrain` độc lập).
  * **`max_hop = 1` (Ưu tiên độ chính xác - Precision)**: Ưu tiên cô lập triệt để các dịch vụ chạy tác vụ nền không liên quan. Nhược điểm là nếu sự cố lan truyền thực sự qua nhiều tầng trung gian mà các node trung gian không bắn alert, hệ thống sẽ bỏ sót và chia cắt sự cố lớn đó thành nhiều cụm độc lập.
  * **Quyết định**: Em đề xuất dùng `max_hop = 1` khi cần lọc nhiễu nghiêm ngặt và `max_hop = 2` khi cần điều tra nguyên nhân diện rộng.

---

## 3. Phân tích Alert bị bỏ sót (Missed/Orphan Alert)
* **Alert ID bị "miss" (trở thành `orphan` / cụm riêng lẻ)**: Alert `a-0013` (service `recommender-svc` với metric `cpu_utilization`).
* **Tại sao?**:
  * Khi em chạy cấu hình với `max_hop = 1`, alert `a-0013` bị cô lập hoàn toàn thành cụm `c-000-001` có kích thước bằng 1.
  * Trên service graph, `recommender-svc` chỉ kết nối trực tiếp với `catalog-svc` và `catalog-db` (khoảng cách 1 `hop`). Tuy nhiên, trong cùng khung giờ đó, cả `catalog-svc` và `catalog-db` đều **không phát sinh bất kỳ alert nào**.
  * Cửa ngõ gần nhất có alert là `edge-lb`, cách `recommender-svc` tới 2 `hops`. Do `max_hop = 1`, thuật toán không thể liên kết chúng lại, biến `a-0013` thành `orphan`. Thực tế điều này hoàn toàn đúng vì nhãn của alert này chỉ rõ: `"note": "unrelated — concurrent batch retrain"`.

---

## 4. Đánh giá hiệu năng với quy mô dữ liệu lớn (10,000 Alerts)
Nếu số lượng alert tăng lên 10,000 thay vì 200, code hiện tại của em sẽ gặp nút thắt cổ chai hiệu năng ở các điểm sau:
1. **Tìm đường đi ngắn nhất (`nx.shortest_path_length`) lặp đi lặp lại**:
   * Thuật toán hiện tại duyệt qua mọi cặp service có alert trong `session` (độ phức tạp `O(S^2)` với `S` là số lượng service). Với mỗi cặp, nó gọi hàm tìm đường đi ngắn nhất trên đồ thị.
   * Nếu số lượng alert lớn và số lượng service tăng lên, việc tính lại đường đi trên Graph nhiều lần sẽ cực kỳ chậm.
   * **Cách tối ưu của em**: Tính trước khoảng cách giữa toàn bộ các cặp node trên đồ thị (`Pre-calculate All-Pairs Shortest Path` bằng `Floyd-Warshall` hoặc `BFS/Dijkstra` chạy một lần duy nhất lúc khởi động đồ thị) và lưu vào một `lookup table` (dictionary/matrix) với độ phức tạp truy xuất `O(1)`.
2. **Kích thước Session phình to**:
   * Nếu 10,000 alert xảy ra liên tục không có khoảng nghỉ `> 120s`, chúng sẽ bị dồn vào một `Session` khổng lồ duy nhất. Khi đó việc tính toán `topology` cho session này sẽ quá tải.
   * **Cách tối ưu của em**: Áp dụng bước `Dedup` (Layer 1) trước để gom các alert trùng lặp lại trước khi đưa vào các bước phân tích `Time-Window` và `Topology`. Việc này sẽ giảm quy mô dữ liệu đầu vào của Layer 2 và 3 từ 10,000 xuống chỉ còn vài chục unique events.

---

## 5. EOD Checkpoint Answers

### Câu 1: Vì sao fingerprint cho dedup không include timestamp hay value? Cho ví dụ nếu include thì hệ thống behave ra sao.
* **Trả lời**: `timestamp` thay đổi mỗi khi alert phát sinh, và `value` đo lường giá trị của metric tại thời điểm đó (cũng thay đổi liên tục). Nếu đưa chúng vào `fingerprint`, mỗi lần alert mới bắn ra sẽ có một `fingerprint` độc nhất vô nhị. Hệ thống sẽ không bao giờ phát hiện được trùng lặp (`Dedup` mất tác dụng), dẫn tới `alert flood` bùng nổ, bộ nhớ lưu trữ phình to vô hạn, gây ra tình trạng `alert fatigue` nghiêm trọng cho các `on-call engineer`.

### Câu 2: Sự khác biệt giữa “duplicate” và “correlated” alert là gì? Ví dụ cụ thể từ lab dataset.
* **Trả lời**:
  * **Duplicate alert**: Là cùng một loại alert (cùng service, metric, severity) lặp đi lặp lại nhiều lần. Ví dụ: `a-0003` và `a-0008` đều là alert của service `payment-svc` với metric `latency_p99_ms` ở mức `crit`. Chúng đại diện cho cùng một triệu chứng (`symptom`) duy nhất kéo dài.
  * **Correlated alert**: Là các alert khác nhau (khác metric, hoặc khác service) nhưng xảy ra đồng thời hoặc có quan hệ phụ thuộc nhân quả, cùng thuộc về một sự cố gốc (`incident`). Ví dụ: `a-0002` (`payment-svc` DB pool used crit) và `a-0005` (`checkout-svc` latency warn). Chúng đại diện cho chuỗi phản ứng dây chuyền (checkout chậm do payment bị nghẽn DB).

### Câu 3: gap_sec = 30 (rất ngắn) vs gap_sec = 600 (rất dài) — mỗi cái sẽ ảnh hưởng output thế nào? 1 dòng cho mỗi case.
* **Trả lời**:
  * Với `gap_sec = 30`: Số lượng cụm (`clusters`) tăng vọt, một sự cố đơn lẻ kéo dài hoặc lan truyền chậm sẽ bị chia cắt thành nhiều cụm nhỏ rời rạc (`false negative`).
  * Với `gap_sec = 600`: Số lượng cụm giảm mạnh, các sự cố hoàn toàn độc lập và cách nhau xa về thời gian sẽ bị gộp nhầm vào một cụm lớn (`false positive`).

### Câu 4: Trong scenario chính (payment-svc pool exhaustion), recommender-svc cũng alert (batch retrain). Correlator của bạn có gom recommender vào cluster chính không? Vì sao có / không?
* **Trả lời**:
  * Nếu sử dụng `max_hop = 2` (mặc định): Có gom recommender-svc vào cluster chính. Lý do là vì khoảng cách ngắn nhất giữa `recommender-svc` và `edge-lb` (service có alert trong cùng session) trên service graph vô hướng là 2 `hops` (`recommender-svc` - `catalog-svc` - `edge-lb`), đạt điều kiện `dist <= max_hop`.
  * Nếu sử dụng `max_hop = 1`: KHÔNG gom recommender-svc vào cluster chính. Lý do là vì khoảng cách ngắn nhất từ `recommender-svc` đến bất kỳ service nào có alert trong cùng session đều lớn hơn hoặc bằng 2 `hops` (`> max_hop = 1`), do đó nó bị cô lập thành cụm riêng (`c-000-001`).

### Câu 5: Limitation lớn nhất của topology grouping mà bạn nhận ra? Suggest 1 cách khắc phục.
* **Trả lời**:
  * **Limitation**: Đồ thị vô hướng (undirected graph) và cơ chế gom cụm bắc cầu (`Union-Find`) dễ dẫn tới hiện tượng gom cụm quá mức (`over-clustering`). Một service ở xa (như `recommender-svc` bị lỗi do `batch retrain` nội bộ) chỉ cần nằm trong khoảng cách `max_hop` với một node rìa nào đó có alert (như `edge-lb`) là sẽ bị kéo vào cụm sự cố chính của `payment-svc` mặc dù chúng không có liên hệ nhân quả.
  * **Khắc phục của em**:
    1. Sử dụng đồ thị có hướng (directed graph) và chỉ cho phép lan truyền ngược hướng gọi (từ downstream lên upstream) hoặc xuôi hướng cascade để phản ánh đúng luồng lỗi.
    2. Kết hợp Layer 4 (`Semantic Similarity`): Kiểm tra mức độ tương đồng về mặt ngữ nghĩa (metric name, mô tả lỗi) hoặc độ ưu tiên của service (`criticality`). Ví dụ, loại bỏ các alerts của service có `criticality: low` (như `recommender-svc`) ra khỏi sự cố nghiêm trọng của core path, hoặc kiểm tra xem có đường đi liên tục chứa toàn các node đang bị alert (`alert path`) hay không thay vì chỉ tính khoảng cách đơn thuần.
