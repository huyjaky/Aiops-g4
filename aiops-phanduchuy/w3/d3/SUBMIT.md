# W3-D3 Submission — Phan Duc Huy

## Outage chosen
- **ID:** 1
- **Name:** AWS S3 us-east-1 (2017-02-28)
- **Why this one:** Tôi chọn sự cố này vì nó phản ánh một pattern cực kỳ phổ biến và nghiêm trọng trong thực tế: thao tác vận hành thủ công của con người (operator action) bị nhầm lẫn đối tượng và lan rộng do thiếu kiểm soát vùng ảnh hưởng (blast radius). Tôi muốn nghiên cứu sâu cách hệ thống giám sát phân biệt giữa lỗi hệ thống tự phát và hành động bảo trì của con người.
- **Failure mode:** operator action without guardrail

## 3 thứ tôi học từ outage này
1. **Dữ liệu vận hành (Operational Context) là bắt buộc:** Một hệ thống AIOps chỉ giám sát metric và log ứng dụng sẽ hoàn toàn mù màu trước các hành động của con người, dẫn đến việc phân tích nguyên nhân gốc rễ (RCA) bị sai lệch hoặc đưa ra cảnh báo "unknown".
2. **Ảnh hưởng của Cold-Start:** Các hệ thống lõi hoạt động liên tục trong nhiều năm (như S3 index và placement) khi bị khởi động lại đột ngột sẽ mất rất nhiều thời gian để kiểm tra tính toàn vẹn dữ liệu (cold-start validation), khiến MTTR kéo dài hơn dự kiến rất nhiều.
3. **Dry-Run và Blast Radius Guardrails:** Bất kỳ công cụ tự động hóa hoặc script bảo trì nào chạy trên môi trường production đều phải tích hợp sẵn cơ chế kiểm tra tham số, chế độ chạy thử (dry-run) và giới hạn cứng số lượng node có thể tác động cùng lúc.

## 1 thứ pipeline của tôi sẽ vẫn miss nếu outage này xảy ra real
- **Pattern:** Operator actions without guardrail (Hành vi dừng dịch vụ thủ công trực tiếp từ CLI).
- **Why miss:** Pipeline hiện tại chỉ giám sát Prometheus metrics và HTTP error rates. Khi operator chạy lệnh `docker compose stop` hoặc tắt container trực tiếp, pipeline sẽ thấy các service đồng thời dừng hoạt động nhưng không có dữ liệu để suy luận xem đây là hành động có chủ đích của con người hay do lỗi crash của hạ tầng vật lý.
- **Mitigation idea:** Xây dựng một đường ống thu thập sự kiện vận hành (Operational Event Stream) từ SSH audit logs (`auditd`), Docker events, Kubernetes API server audit, và CI/CD deployment logs để làm đầu vào đối sánh thời gian (temporal correlation) trong công cụ RCA.

## 1 quyết định trong ADR mà tôi không hoàn toàn chắc
- **Quyết định tích hợp SSH/shell audit logs trực tiếp vào pipeline:** Tôi lo ngại về vấn đề bảo mật và rò rỉ dữ liệu nhạy cảm. Việc lưu lại toàn bộ các lệnh chạy trên terminal của operator có thể vô tình ghi nhận các thông tin mật (như tokens, API keys, password truyền dưới dạng argument) vào log hệ thống, đòi hỏi phải có cơ chế lọc (redaction) cực kỳ phức tạp và đáng tin cậy ở client-side trước khi truyền về AIOps pipeline.

## Cost model verdict cho stack của tôi (E-Commerce Platform)
- **ROI:** 9.0
- **Payback:** 0.11 tháng (~3 ngày)
- **Verdict:** worth_it
