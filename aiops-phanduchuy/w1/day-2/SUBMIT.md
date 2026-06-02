## plot template count time series, anomaly highlighted
<img width="1489" height="1189" alt="image" src="https://github.com/user-attachments/assets/eb4a7546-cac0-4a15-bbb3-698f701c7c87" />

## output Drain3 (số template, top-10), tuning log (sim_th values + kết quả)

### số template, tuning log (sim_th values + kết quả)
```
Ground Truth unique templates count: 120
Similarity Threshold: 0.1 -> Generated 120 templates
Similarity Threshold: 0.3 -> Generated 120 templates
Similarity Threshold: 0.5 -> Generated 120 templates
Similarity Threshold: 0.7 -> Generated 466 templates

Best similarity threshold: 0.1 (produces 120 templates, closest to 120)
```

## top-10
<img width="1409" height="378" alt="image" src="https://github.com/user-attachments/assets/8aa49732-7630-4843-9d22-af2b0e5aff1f" />

## Evaluation on Window-level Anomaly Detection
```
              precision    recall  f1-score   support

         0.0       0.90      0.91      0.91       736
         1.0       0.22      0.19      0.20        95

    accuracy                           0.83       831
   macro avg       0.56      0.55      0.56       831
weighted avg       0.82      0.83      0.83       831
```

## Find Template Clusters
```
--- Template Clusters ---

Cluster 0:
  - instruction cache parity error corrected
  - CE sym <*>, at <*>, mask <*>
  - ciod: failed to read message prefix on control stream (CioStream socket to <*>.<*>.<*>.<*>
  ... (total 74 templates)

Cluster 1:
  - force load/store alignment...............<*>
  - data TLB error interrupt
  - data storage interrupt
  ... (total 13 templates)

Cluster 2:
  - <*> ddr errors(s) detected and corrected on rank <*>, symbol <*>, bit <*>
  - total of <*> ddr error(s) detected and corrected
  - <*> torus receiver z+ input pipe error(s) (dcr <*>) detected and corrected
  ... (total 12 templates)

Cluster 3:
  - data address: <*>
  - data address: <*>
  - data address: <*>
  ... (total 10 templates)

Cluster 4:
  - critical input interrupt enable...<*>
  - suppressing further interrupts of same type
  - critical input interrupt (unit=<*> bit=<*>): warning for torus y+ wire
  ... (total 7 templates)

Cluster 5:
  - <*> <*> alignment exceptions
  - <*> <*> alignment exceptions
  - <*> <*> alignment exceptions
  ... (total 109 templates)

Cluster 6:
  - ciod: LOGIN <*> failed: No such file or directory
  - ciod: Error loading /home/draeger/<*>: invalid or missing program image, No such file or directory
  - ciod: Error loading ./runtime_malloc: invalid or missing program image, No such file or directory
  ... (total 7 templates)

Cluster 7:
  - iar <*> dear <*>
  - iar <*> dear <*>
  - iar <*> dear <*>
  ... (total 209 templates)

Cluster 8:
  - Ido chip status changed: <*> ip=<*>.<*>.<*>.<*> v=<*> t=<*> status=M Fri Jul <*> <*> PDT <*>
  - Ido chip status changed: <*> ip=<*>.<*>.<*>.<*> v=<*> t=<*> status=M Thu Aug <*> <*> PDT <*>
  - Ido chip status changed: <*> ip=<*>.<*>.<*>.<*> v=<*> t=<*> status=M Tue Aug <*> <*> PDT <*>
  ... (total 4 templates)

Cluster 9:
  - instruction address: <*>
  - instruction address: <*>
  - instruction address: <*>
  ... (total 21 templates)
```

### SCRIPT 
```
py log_analyzer.py BGL/BGL_2k.log
=== Log Analyzer ===
File: BGL/BGL_2k.log | Type: BGL
Mining templates...
\n[1] General Statistics:
Total lines: 2000
Unique templates: 105
\n[2] Top-5 Templates:
  - [720 times | 36.0%] generating <*>
  - [207 times | 10.3%] iar <*> dear <*>
  - [108 times | 5.4%] <*> double-hummer alignment exceptions
  - [91 times | 4.5%] CE sym <*> at <*> mask <*>
  - [84 times | 4.2%] <*> floating point alignment exceptions
\n[3] Anomaly Detection (Last 1 hour):
  Time frame evaluated (Last hour): 2006-01-03 22:00:00
  * Spiked templates (> Mean + 3 Std):
    - ciod: generated <*> core files for program <*> (Count: 1, Avg: 0.1)
  * New Templates (Never seen before):
    None.
```

```
py log_analyzer.py HDFS/HDFS_2k.log
=== Log Analyzer ===
File: HDFS/HDFS_2k.log | Type: HDFS
Mining templates...
\n[1] General Statistics:
Total lines: 2000
Unique templates: 17
\n[2] Top-5 Templates:
  - [310 times | 15.5%] PacketResponder <*> for block <*> terminating
  - [300 times | 15.0%] BLOCK* NameSystem.addStoredBlock: blockMap updated: <*> is added to <*> size <*>
  - [291 times | 14.5%] Receiving block <*> src: <*> dest: <*>
  - [280 times | 14.0%] Received block <*> of size <*> from <*>
  - [262 times | 13.1%] Deleting block <*> file <*>
\n[3] Anomaly Detection (Last 1 hour):
  Time frame evaluated (Last hour): 2008-11-11 10:00:00
  * Spiked templates (> Mean + 3 Std):
    None.
  * New Templates (Never seen before):
    None.
```

## Drain3 parse tốt không, template nào cho insight, metric vs log khác gì
### rain3 parse có tốt không? 
-> Rất tốt và nhanh, nhưng phụ thuộc hoàn toàn vào Masking Rules với những log có service dày đặt. Nhờ việc tạo ra Rule chuẩn em đã dễ dàng tạo ra các template chuẩn xác. Nếu không có rule, nó sẽ sinh ra vô số template rác.
### 2. Template mới hoàn toàn, Template tăng đột biến
- Template mới hoàn toàn: Giúp phát hiện ngay những mẫu log chưa từng xuất hiện trước đây, giúp nhận diện sớm các lỗi bất thường, lỗ hổng zero-day hoặc hành vi tấn công mới của hacker. 
- Template tăng đột biến: Theo dõi sự thay đổi tần suất xuất hiện của các mẫu log theo thời gian để cảnh báo sớm các sự cố tiềm ẩn. Chẳng hạn, trong Phase 4, hệ thống đã phát hiện template "dump core" tăng mạnh vào giờ cuối cùng, cho thấy nguy cơ hệ thống gặp lỗi nghiêm trọng hoặc sắp xảy ra sự cố.
### 3. Metric vs Log khác gì và kết hợp được gì?
- Metric: Là những con số đếm. Nó nhẹ, load nhanh, đóng vai trò làm chuông báo động đỏ.
- Log: Là câu chữ chi tiết. Nó nặng, khó đọc, đóng vai trò làm camera an ninh để tìm kím nguyên nhân gốc rễ.
- Khi kết hợp: Metric giúp em biết chính xác phút nào hệ thống có vấn đề, sau đó em map sang Log để xem nguyên nhân là template lỗi nào. Điều này giúp tự động hóa quá trình debug thay vì phải đọc thủ công từng dòng.


## BONUS
### Parse log từ 1 ứng dụng thật mà bạn có (Docker log, nginx log, application log) — không dùng Loghub
```
py portainer_parser.py
Mining templates for Portainer logs...
\n--- LOG PARSING RESULTS ---
Total templates found: 16
\nTemplate List:
[27 times] failure to close resource | <*>
[23 times] session ended |
[10 times] starting <*> server | <*>
[ 5 times] Listening on http://0.0.0.0:8000
[ 5 times] executing post init migration for environment | <*>
[ 5 times] starting Portainer | <*> <*> <*> <*> <*> <*> webpack_<*>
[ 4 times] encryption key file not present | filename=/run/secrets/portainer
[ 4 times] proceeding without encryption key |
[ 4 times] loading PortainerDB | filename=portainer.db
[ 4 times] found Chisel private key file on disk | private-key=/data/chisel/private-key.pem
[ 4 times] Reverse tunnelling enabled
[ 1 times] <*>
[ 1 times] <*>
[ 1 times] <*>
[ 1 times] <*>
[ 1 times] <*>
```
## Knowledge check 
<img width="2268" height="4388" alt="image" src="https://github.com/user-attachments/assets/c499dae3-498f-434e-8e6c-08baffa68c1c" />
<img width="2802" height="4538" alt="image" src="https://github.com/user-attachments/assets/f2c7c267-2ddc-4223-a701-4910d65fbe9d" />
<img width="2204" height="1393" alt="image" src="https://github.com/user-attachments/assets/af57785a-2b41-48a0-ba05-9341aa5760b7" />
<img width="1440" height="1303" alt="image" src="https://github.com/user-attachments/assets/cc8fe782-f7f3-487f-9ad5-105896757108" />
<img width="1593" height="1812" alt="image" src="https://github.com/user-attachments/assets/4e2c1cee-c008-4608-933d-4405b8e14a05" />




