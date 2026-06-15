# SLO and Alerting Design Document (DESIGN.md)

Tài liệu này giải thích các quyết định thiết kế cho hệ thống SLI/SLO và cơ chế cảnh báo Multi-Window Multi-Burn-Rate (MWMBR) dựa trên phân tích dữ liệu thực tế thu được từ `baseline.json` và kết quả chạy thử nghiệm trong `validation_report.json`.

---

### 1. SLI choice cho frontend
Đối với frontend, tín hiệu RUM cung cấp 4 metric ứng viên bao gồm: page load time, DOM ready, JS error rate và network error rate. Chúng tôi quyết định chọn tiêu chuẩn đánh giá sự khả dụng (availability) dựa trên sự kết hợp: `dom_ready < 3000ms AND no js_error AND no network_error`.

Lý do loại bỏ các phương án khác:
- **Page load time:** Quá rộng, dễ bị nhiễu bởi các script quảng cáo hoặc theo dõi từ bên thứ ba mà không ảnh hưởng trực tiếp đến tương tác chính của người dùng.
- **JS error rate & Network error rate:** Nếu đứng riêng lẻ thì chỉ bắt được một góc nhỏ của vấn đề (lỗi script hoặc lỗi mạng), bỏ qua trường hợp trang tải cực kỳ chậm nhưng không báo lỗi.

Kết hợp 3 yếu tố giúp đo lường chính xác trải nghiệm thực tế của người dùng (user pain). Theo `baseline.json`, frontend có tổng số **518.400 events** với **7.204 sự kiện lỗi** (tỷ lệ lỗi ~1.39%), p99 DOM ready đạt **1430ms**. Ngưỡng 3000ms là khoảng đệm an toàn (gấp ~2 lần p99) để phát hiện bất kỳ sự suy giảm hiệu năng nghiêm trọng nào từ phía CDN/Frontend mà không gây báo động giả.

---

### 2. SLO target cho api
Chúng tôi đặt mục tiêu SLO khả dụng cho API là **99.9%** trong chu kỳ 30 ngày.

Lý do lựa chọn:
- Nếu đặt **99.0%** (2 số 9), hệ thống cho phép tới 432 phút downtime/tháng. Ngưỡng này quá lỏng lẻo, khiến on-call engineer không nhận được cảnh báo ngay cả khi API bị sập một khoảng thời gian dài, gây mất mát doanh thu nghiêm trọng.
- Nếu đặt **99.99%** (4 số 9), thời gian downtime tối đa chỉ còn 4.3 phút/tháng. Điều này đòi hỏi kiến trúc Multi-AZ, Multi-Region active-active và đội ngũ SRE trực 24/7, đẩy chi phí vận hành tăng từ 3-10 lần.
- Trong khi đó, `baseline.json` chỉ ra tỷ lệ thành công của API trong điều kiện bình thường (không tính thời gian xảy ra 5 sự cố lớn) đạt **99.85%**. Do đó, SLO **99.9%** là lựa chọn tối ưu nhất, vừa phản ánh đúng năng lực hiện tại của hệ thống (4 instances FastAPI + DB primary/replica), vừa cân bằng giữa chi phí hạ tầng và trải nghiệm người dùng.

---

### 3. Latency threshold p99
Chúng tôi thiết lập ngưỡng cắt (cut-off) độ trễ của API ở mốc **500ms** để phân loại các yêu cầu bị coi là chậm (failure).

Dưới đây là bảng phân phối độ trễ (latency distribution) của API thu thập từ 2.073.780 request trong 3 ngày:
- **p50 (Median):** 45 ms
- **p90:** 86 ms
- **p95:** 104 ms
- **p99 (Tail latency):** 156 ms
- **p99.9:** 394 ms

Biện hộ cho lựa chọn 500ms:
Số liệu thực tế cho thấy ngay cả ở phân vị p99.9, độ trễ tối đa của request cũng chỉ đạt 394ms (vẫn nhỏ hơn 500ms). Việc chọn 500ms làm mốc cắt là vô cùng hợp lý, vì nó lớn gấp ~3.2 lần so với p99 (156ms). Ngưỡng này đảm bảo loại bỏ hoàn toàn các dao động độ trễ ngẫu nhiên trong mạng (network jitter) ở điều kiện bình thường, đồng thời phát hiện chính xác các hiện tượng suy giảm hiệu năng hệ thống như nghẽn luồng xử lý hoặc chậm truy vấn DB trong các incident thực tế.

---

### 4. 4xx exclusion
Chúng tôi loại trừ toàn bộ mã lỗi nhóm 4xx ra khỏi danh sách tính lỗi của SLI/SLO khả dụng API, ngoại trừ mã **429 (Too Many Requests)**.

Lý do:
- Các mã lỗi như 400, 401, 403, 404 phản ánh lỗi xuất phát từ phía client (nhập sai URL, thiếu token, bad request). Hệ thống hoạt động hoàn toàn bình thường nhưng vẫn phải trả về các mã lỗi này theo chuẩn HTTP. Nếu tính cả 4xx vào SLO, bất kỳ cuộc tấn công dò quét cổng (port scanning) hoặc bot spam request nào cũng sẽ nhanh chóng đốt cháy Error Budget của hệ thống, dẫn đến cảnh báo giả gây mệt mỏi cho đội ngũ on-call (alert fatigue).
- Số liệu thực tế từ `access_log.jsonl` chứng minh tỷ lệ lỗi 4xx duy trì ổn định ở mức **~2.0%** trên tất cả các endpoint (như `/api/orders`: 2.02%, `/api/products`: 2.02%) do bot/scraper tạo ra định kỳ. 
- Ngược lại, lỗi **429** được giữ lại vì nó cho thấy hệ thống đang phải từ chối người dùng do quá tải tài nguyên, cần được SRE theo dõi để scale-up kịp thời.

---

### 5. MWMBR tuning
Chúng tôi sử dụng bộ tham số mặc định được Google SRE khuyến nghị:
- **Tier 1 (Urgent Page):** Long window 1h, Short window 5m, Threshold 14.4 (tiêu thụ 2% budget).
- **Tier 2 (Page):** Long window 6h, Short window 30m, Threshold 6.0 (tiêu thụ 5% budget).
- **Tier 3 (Ticket):** Long window 3d, Short window 6h, Threshold 1.0 (tiêu thụ 10% budget).

Lý do không thay đổi tham số:
Kết quả từ `validation_report.json` khi chạy bộ tham số này đạt hiệu quả xuất sắc:
- **Tỷ lệ giảm nhiễu (noise_reduction_pct) đạt 86.4%** (vượt xa yêu cầu tối thiểu 70%), chỉ kích hoạt **3 cảnh báo** so với **22 cảnh báo** của baseline tĩnh.
- **Tỷ lệ bỏ sót sự cố (False Negative - FN) bằng 0**, phát hiện thành công cả 3 incident nghiêm trọng ảnh hưởng đến API.
- **Độ trễ phát hiện sự cố (mttd_delta_s) là 60 giây**, nằm đúng trong giới hạn cho phép (<= 60s).

Nếu ta tăng ngưỡng burn rate (ví dụ lên 20.0), mttd_delta_s sẽ bị kéo dài hoặc thậm chí dẫn đến bỏ sót sự cố nhỏ (FN > 0). Ngược lại, nếu giảm ngưỡng xuống để phát hiện nhanh hơn, số lượng cảnh báo giả sẽ tăng lên, làm giảm `noise_reduction_pct` xuống dưới mức 70%. Bộ cấu hình mặc định này đã tối ưu hoàn hảo cho tập dữ liệu của chúng ta.
