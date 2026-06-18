# DESIGN.md — Ronki Closed-Loop Orchestrator Design Defense

## 1. Decision engine: Rule-based hay LLM-based?

**Chọn: Rule-based.**

### Lý do lựa chọn:
Hệ thống sản xuất của Ronki hiện tại có 3 loại cảnh báo được định nghĩa rất rõ ràng (`HighLatency`, `HighErrorRate`, `InstanceDown`) và mỗi loại tương ứng trực tiếp với 1 hành động/runbook cụ thể đã được đội ngũ vận hành (Ops) kiểm chứng thực tế. Trong môi trường này, giải pháp Rule-based mang lại:
- **Tốc độ quyết định cực kỳ nhanh (< 1ms)** so với việc gọi API LLM (thường mất từ 200–800ms).
- **Tính ổn định và chính xác (Deterministic - 100%)**: Cùng một sự kiện cảnh báo sẽ luôn kích hoạt cùng một runbook tương ứng, không có rủi ro ngẫu nhiên hay phụ thuộc vào nhiệt độ (temperature) của mô hình.
- **Không tốn chi phí vận hành** cũng như không phụ thuộc vào kết nối mạng bên ngoài (hạn chế rủi ro lỗi mạng khi kết nối tới API của Anthropic/Claude).

### Bảng so sánh Trade-offs:

| Tiêu chí | Rule-based | LLM-based |
|---|---|---|
| **Độ trễ quyết định** | < 1ms | 200–800ms (API Round-trip) |
| **Tính nhất quán (Determinism)** | 100% | Dao động phụ thuộc prompt, model |
| **Khả năng mở rộng cảnh báo mới** | Thủ công cập nhật ánh xạ | Tự suy luận nếu prompt đủ tốt |
| **Chi phí** | Miễn phí | Tốn phí theo token |
| **Khả năng hoạt động ngoại tuyến** | Hoạt động tốt | Cần cơ chế fallback rule-based khi offline |

**Kết luận:** Với quy mô 5 dịch vụ và 3 loại cảnh báo cố định cần tính tin cậy tuyệt đối, Rule-based là lựa chọn tối ưu nhất. Nếu hệ thống mở rộng lên hàng chục hoặc hàng trăm loại cảnh báo không đồng nhất với mô tả ngôn ngữ tự nhiên phức tạp, mô hình LLM-based sẽ được cân nhắc làm lớp quyết định cấp cao (với ngưỡng tin cậy confidence >= 0.6) và có cơ chế fallback về Rule-based.

---

## 2. Blast-radius config

Cấu hình Blast-radius được thiết lập trong `config.yaml` như sau:
```yaml
blast_radius:
  max_actions_per_minute: 3
  max_restarts_per_service_per_hour: 5
```

### Lý do lựa chọn các giá trị này:
- `max_actions_per_minute: 3` — Tổng số hành động tối đa mà hệ thống tự động hóa được phép kích hoạt trên toàn bộ 5 dịch vụ trong vòng 1 phút là 3. Trong trường hợp xảy ra lỗi dây chuyền (cascade failure), giới hạn này giúp ngăn chặn tình trạng orchestrator khởi động lại đồng loạt tất cả các container cùng lúc, gây quá tải (thundering herd) lên hệ thống cơ sở dữ liệu hoặc gateway. Con số 3 đủ để hệ thống phản ứng nhanh với tối đa 3 dịch vụ bị lỗi độc lập cùng lúc mà vẫn đảm bảo an toàn.
- `max_restarts_per_service_per_hour: 5` — Giới hạn số lần khởi động lại của một dịch vụ đơn lẻ trong vòng 1 giờ là 5. Nếu một dịch vụ bị lỗi và phải khởi động lại quá 5 lần trong 1 giờ mà vẫn tiếp tục gặp lỗi, điều này chỉ ra một lỗi nghiêm trọng không thể tự phục hồi (ví dụ: lỗi cấu hình sai, OOM liên tục do rò rỉ bộ nhớ, hoặc cơ sở dữ liệu phía sau bị sập). Tiếp tục restart sẽ không giải quyết được vấn đề mà chỉ gây tốn tài nguyên và che giấu lỗi gốc — lúc này hệ thống cần tạm dừng hành động tự động và leo thang (escalate) cảnh báo tới kỹ sư trực vận hành.

---

## 3. Verify step

### Cấu hình kiểm tra:
Hệ thống kiểm tra đồng thời hai chỉ số từ Prometheus để đánh giá độ thành công của hành động tự động:
1. **p99 Latency (Độ trễ phân vị thứ 99):**
   - **Metric:** `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{service="{service}"}[1m])) * 1000` (ms).
   - **Threshold:** Độ trễ p99 phải dưới **500ms** (dựa trên dữ liệu `baseline.json`, độ trễ p99 của các dịch vụ ở trạng thái khỏe mạnh dao động từ 72ms đến 230ms. Ngưỡng 500ms gấp đôi độ trễ của dịch vụ chậm nhất là `checkout-svc`, giúp tránh hiện tượng cảnh báo nhầm khi tải tăng nhẹ nhưng vẫn phát hiện được khi có sự cố nghẽn).
2. **Trạng thái Up/Down (Reachability):**
   - **Metric:** `up{job="{service}"}`.
   - **Threshold:** Phải đạt giá trị **1** (nghĩa là Prometheus scrape thành công dịch vụ đó).

### Timeout và Polling:
- `verify_timeout_seconds: 60` (Timeout 60 giây) — Khởi động lại một container mất từ 5–10 giây, và Prometheus cần 15–20 giây tiếp theo để thu thập và tính toán lại các metric (scrape interval là 10 giây). Thời gian 60 giây đủ cho ít nhất 3-4 chu kỳ scrape của Prometheus sau khi dịch vụ online trở lại.
- `verify_poll_interval_seconds: 10` — Trùng khớp với tần suất scrape của Prometheus để tối ưu hóa việc truy vấn và tránh quá tải API của Prometheus.
- `verify_min_samples: 3` — Yêu cầu ít nhất **3 mẫu thử liên tiếp** đạt trạng thái khỏe mạnh trước khi kết luận hành động thành công. Điều này ngăn chặn tình trạng "mẫu thử may mắn" (false positive) khi dịch vụ mới khởi động lại và tải chưa đổ về hoàn toàn.

---

## 4. Circuit breaker reset

**Lựa chọn: Manual reset (Khôi phục thủ công).**

### Lý do lựa chọn:
Cầu chì (Circuit breaker) được thiết kế để ngắt tự động hóa sau **3 lần thất bại liên tiếp** (`consecutive_failure_threshold: 3`). Khi cầu chì chuyển sang trạng thái `CIRCUIT_OPEN`, điều này có nghĩa hệ thống tự động hóa đã thực hiện các runbooks và rollback nhưng lỗi vẫn tiếp tục lặp lại. Đây là dấu hiệu của sự cố hệ thống nghiêm trọng.

Nếu cấu hình tự động reset cầu chì (ví dụ: sau 30 phút), orchestrator sẽ tự động chạy lại các runbook đó, có khả năng tạo ra một vòng lặp khởi động lại vô hạn (infinite restart loop), gây kiệt quệ tài nguyên kết nối của cơ sở dữ liệu, phá vỡ tính toàn vẹn dữ liệu, hoặc khiến sự cố lan rộng hơn.

Manual reset đảm bảo rằng một kỹ sư trực vận hành phải nhảy vào kiểm tra log, phân tích nguyên nhân gốc rễ, sửa lỗi triệt để, và sau đó khởi động lại orchestrator (`Ctrl+C` và chạy lại `uv run python closed_loop.py`). Chi phí của vài phút trễ do thao tác tay là cực kỳ nhỏ so với rủi ro hệ thống bị sập hoàn toàn do tự động hóa hoạt động sai lệch liên tục.

---

## 5. Mutex strategy (Stress 5 — concurrent alert race)

### Thiết kế:
Hệ thống sử dụng một bản đồ chứa các khóa `threading.Lock()` tương ứng với từng dịch vụ (`_service_locks`), được bảo vệ bởi một khóa meta-lock (`_locks_meta`) để tránh tranh chấp khi tạo khóa. Khi có cảnh báo mới đến:
- Orchestrator gọi phương thức `acquire(blocking=False)`.
- Nếu khóa của dịch vụ đó đang được nắm giữ bởi một luồng xử lý runbook khác, orchestrator sẽ log sự kiện `SERVICE_LOCK_BUSY` và bỏ qua cảnh báo trùng lặp đó ngay lập tức.
- Các dịch vụ khác nhau (ví dụ: `payment-svc` và `inventory-svc`) sẽ có các khóa độc lập và được xử lý trong các luồng (thread) song song không hề chặn lẫn nhau.

### Lý do dùng `blocking=False` thay vì hàng đợi (Queue):
Trong cơ chế closed-loop, một runbook đang thực thi trên dịch vụ A đại diện cho một hành động khắc phục đang diễn ra. Bất kỳ cảnh báo nào xuất hiện trên dịch vụ A trong thời gian runbook chạy đều là cảnh báo trùng lặp của cùng một sự cố gốc rễ. Việc xếp hàng đợi (queue) sẽ khiến runbook chạy lại ngay sau khi khóa được giải phóng, dẫn đến việc khởi động lại dịch vụ 2 lần liên tiếp không cần thiết và gây nguy hiểm cho hệ thống. Bỏ qua cảnh báo trùng lặp và để luồng hiện tại hoàn thành Verify/Rollback là giải pháp an toàn nhất.

---

## 6. Rollback chain ordering (Stress 4 — multi-step transactional deploy)

### Thiết kế:
Khi thực hiện một chuỗi triển khai gồm nhiều bước (A → B → C), orchestrator ghi nhận danh sách các bước đã hoàn thành thành công vào một danh sách `completed`. Nếu một bước bất kỳ bị thất bại (ví dụ: bước C bị lỗi):
- Orchestrator sẽ lấy danh sách các bước rollback tương ứng với các bước đã hoàn tất (`rollback_steps[:len(completed)]`).
- Kích hoạt các bước rollback theo thứ tự đảo ngược (`reversed()`), tức là rollback bước B trước, sau đó rollback bước A.
- Hoàn toàn không thực hiện rollback cho bước C vì bước C chưa từng hoàn thành thành công.

### Lý do kỹ thuật:
Thứ tự đảo ngược (LIFO - Last In First Out) là nguyên tắc cơ bản của việc hủy giao dịch (transaction rollback). Ví dụ, bước A (dịch chuyển traffic ra khỏi dịch vụ) là tiền đề để bước B (thay đổi cấu hình) diễn ra an toàn. Khi rollback, chúng ta phải đưa cấu hình về trạng thái cũ (rollback B) trước rồi mới cho phép nhận traffic trở lại (rollback A). Nếu rollback A trước B, dịch vụ sẽ nhận traffic khi cấu hình vẫn đang bị lỗi hoặc không nhất quán, gây ra cascade failure ngay lập tức.

---

## 7. Metrics cho observability

Năm metric Prometheus được chọn đều nhằm mục đích giải quyết một câu hỏi debug cụ thể của kỹ sư vận hành:
1. `closed_loop_actions_total{outcome}`: Cho biết nhanh orchestrator đang chạy bình thường, đang chạy thử (`dry_run`), đã xử lý thành công (`success`), hay đang phải rollback (`rollback`).
2. `closed_loop_circuit_breaker_state`: Cảnh báo ngay lập tức nếu cầu chì bị ngắt (`state=1`). Nếu cầu chì mở, kỹ sư biết hệ thống tự động đang bị khóa và cần can thiệp thủ công.
3. `closed_loop_blast_radius_remaining`: Đo lường số hành động còn lại trong chu kỳ giới hạn. Nếu giá trị này tiến dần về 0, hệ thống tự động đang hoạt động quá mức và sắp chạm ngưỡng an toàn.
4. `closed_loop_mutex_locked`: Giúp kiểm tra xem có runbook nào bị treo trên một dịch vụ cụ thể hay không (nếu khóa bị giữ quá lâu).
5. `closed_loop_verify_status`: Trả về trạng thái của bước kiểm tra hiện tại (0=fail, 1=pass, 2=in_progress).

---

## 8. Decision validation policy (Stress 6 — LLM hallucination defense)

### Thiết kế:
Trước khi gọi chạy thử (`dry-run`), hàm `validate_runbook` trích xuất tên kịch bản từ hành động được chọn (lấy token đầu tiên của chuỗi lệnh) và đối chiếu với danh sách trắng (`runbook_registry`) được định nghĩa rõ ràng trong cấu hình `config.yaml`.
- Nếu tên runbook không khớp với bất kỳ script nào trong registry, orchestrator lập tức ghi nhận sự kiện lỗi `DECISION_VALIDATION_FAILED` kèm thông tin chi tiết (`bad_runbook`, `alertname`, `raw_decision`, `action="escalate_no_auto_action"`).
- Tiến trình tự động hóa bị ngắt ngay lập tức đối với cảnh báo đó: Không chạy thử, không spawn subprocess, không làm thay đổi trạng thái cầu chì (vì đây là lỗi của bộ quyết định chứ không phải lỗi của dịch vụ).

### Lý do kỹ thuật:
Các mô hình ngôn ngữ lớn (LLM) có thể tự sinh ra các tên kịch bản rất hợp lý về mặt ngữ nghĩa nhưng không tồn tại trong hệ thống (hallucination, ví dụ: `reboot_database.sh`). Nếu orchestrator chuyển trực tiếp tên này vào lệnh gọi subprocess, bash sẽ báo lỗi `File not found` (exit code khác 0). Lỗi này nếu không được validate trước sẽ bị tính vào số lần thất bại của cầu chì, có khả năng làm ngắt cầu chì một cách oan uổng. Kiểm tra danh sách trắng trước dry-run giúp ngăn chặn triệt để rủi ro này và bảo toàn tính toàn vẹn của tiến trình kiểm soát.

---

## 9. Hyperparameters & Environment Configuration (.env)

Hệ thống hỗ trợ cấu hình động toàn bộ các hyperparameters và cài đặt môi trường thông qua tệp tin `.env`. Các biến môi trường này khi được khai báo sẽ tự động ghi đè (override) lên các giá trị cấu hình mặc định trong `config.yaml` và `baseline.json`.

### Các tham số cấu hình được hỗ trợ trong `.env`:
- **Kết nối hệ thống:**
  - `ALERTMANAGER_URL`: Địa chỉ API của Alertmanager.
  - `PROMETHEUS_URL`: Địa chỉ API của Prometheus.
  - `POLL_INTERVAL_SECONDS`: Tần suất quét Alertmanager để tìm cảnh báo mới.
  - `RUNBOOK_TIMEOUT_SECONDS`: Giới hạn thời gian tối đa chạy mỗi kịch bản.
  - `AUDIT_LOG_PATH`: Đường dẫn lưu trữ tệp tin log JSON có cấu trúc.
- **Giới hạn an toàn (Blast Radius):**
  - `MAX_ACTIONS_PER_MINUTE`: Số hành động tối đa trên toàn hệ thống trong 1 phút.
  - `MAX_RESTARTS_PER_SERVICE_PER_HOUR`: Số lần khởi động lại tối đa của 1 dịch vụ trong 1 giờ.
- **Cầu chì bảo vệ (Circuit Breaker):**
  - `CONSECUTIVE_FAILURE_THRESHOLD`: Số lần lỗi xác thực liên tiếp trước khi ngắt tự động hóa.
- **Observability:**
  - `METRICS_PORT`: Cổng chạy HTTP server để Prometheus scrape các metrics của closed-loop orchestrator.
- **Tham số Verify (Ngưỡng chất lượng dịch vụ):**
  - `VERIFY_TIMEOUT_SECONDS`: Thời gian tối đa chờ dịch vụ phục hồi và ổn định.
  - `VERIFY_POLL_INTERVAL_SECONDS`: Tần suất truy vấn Prometheus trong tiến trình xác thực.
  - `VERIFY_MIN_SAMPLES`: Số mẫu đo liên tục khỏe mạnh để kết luận thành công.
  - `LATENCY_P99_MAX_MS`: Ngưỡng độ trễ p99 tối đa cho phép của dịch vụ.
  - `ERROR_RATE_MAX_PCT`: Ngưỡng tỷ lệ lỗi tối đa cho phép của dịch vụ.
  - `UP_REQUIRED`: Trạng thái reachability bắt buộc (1 = online).

### Ưu điểm thiết kế:
1. **Tách biệt cấu hình và mã nguồn:** Cho phép thay đổi hành vi hoạt động của orchestrator mà không cần chỉnh sửa mã nguồn Python hoặc tệp cấu hình YAML tĩnh.
2. **Khả năng cấu hình động theo môi trường:** Dễ dàng triển khai trên môi trường Local, Staging hoặc Production chỉ bằng cách thay đổi tệp `.env`.
3. **Cơ chế nạp thông minh:** Hàm `load_dotenv()` tự động ưu tiên nạp tệp `.env` tại thư mục làm việc hiện tại trước, sau đó fallback về thư mục chứa mã nguồn của script, đảm bảo orchestrator luôn tìm thấy cấu hình dù chạy từ bất kỳ thư mục nào.

