# SUBMIT.md — Kết quả chạy 6 kịch bản closed-loop auto-remediation

## Thông tin sinh viên
- **Họ tên:** Phan Duc Huy
- **Mã sinh viên:** XB-DN26-078
- **Decision engine:** Rule-based (`runbook_map` trong `config.yaml`)
- **Python version:** 3.13.5 (CPython)
- **Công cụ chạy:** uv 0.4.x, Docker Compose v2.27

---

## 1. Scenario 1 — Action thành công (latency inject trên payment-svc)

**Cách thức thực hiện:**
1. Kích hoạt môi trường và khởi chạy orchestrator:
   `AUDIT_LOG_PATH=../audit_logs/audit_log.jsonl uv run python closed_loop.py --config config.yaml`
2. Sử dụng container Alpine đặc quyền để vào network namespace của `payment-svc` (PID `213004`) và thêm độ trễ 500ms:
   `docker run --rm --privileged --pid=host alpine sh -c "apk add iproute2 && nsenter -t 213004 -n tc qdisc add dev eth0 root netem delay 500ms"`
3. Gửi cảnh báo `HighLatency` cho `payment-svc` vào Alertmanager.

**Log orchestrator:**
```json
{"ts": "2026-06-18T03:08:50.203301Z", "level": "INFO", "event_type": "ALERT_DETECTED", "alertname": "HighLatency", "service": "payment-svc", "severity": "warning"}
{"ts": "2026-06-18T03:08:50.203707Z", "level": "INFO", "event_type": "DECIDE_RUNBOOK", "alertname": "HighLatency", "service": "payment-svc", "runbook": "runbooks/restart_service.sh"}
{"ts": "2026-06-18T03:08:50.205057Z", "level": "INFO", "event_type": "BLAST_RADIUS_OK", "service": "payment-svc"}
{"ts": "2026-06-18T03:08:50.205267Z", "level": "INFO", "event_type": "RUNBOOK_EXEC", "script": "runbooks/restart_service.sh", "service": "payment-svc", "dry_run": true}
{"ts": "2026-06-18T03:08:50.210086Z", "level": "INFO", "event_type": "RUNBOOK_RESULT", "script": "runbooks/restart_service.sh", "service": "payment-svc", "returncode": 0, "stdout": "[DRY-RUN] would execute: docker restart ronki-payment-svc", "stderr": ""}
{"ts": "2026-06-18T03:08:50.210287Z", "level": "INFO", "event_type": "DRY_RUN_PASS", "runbook": "runbooks/restart_service.sh", "service": "payment-svc"}
{"ts": "2026-06-18T03:08:50.210493Z", "level": "INFO", "event_type": "RUNBOOK_EXEC", "script": "runbooks/restart_service.sh", "service": "payment-svc", "dry_run": false}
{"ts": "2026-06-18T03:09:06.201507Z", "level": "INFO", "event_type": "RUNBOOK_RESULT", "script": "runbooks/restart_service.sh", "service": "payment-svc", "returncode": 0, "stdout": "[restart_service] Restarting ronki-payment-svc...\nronki-payment-svc\n[restart_service] Waiting 5s for ronki-payment-svc to come up...\n[restart_service] ronki-payment-svc is running.", "stderr": ""}
{"ts": "2026-06-18T03:09:06.201796Z", "level": "INFO", "event_type": "ACTION_EXECUTED", "runbook": "runbooks/restart_service.sh", "service": "payment-svc"}
{"ts": "2026-06-18T03:09:06.202121Z", "level": "INFO", "event_type": "VERIFY_START", "service": "payment-svc", "timeout_s": 60}
{"ts": "2026-06-18T03:09:06.213494Z", "level": "INFO", "event_type": "VERIFY_SAMPLE", "service": "payment-svc", "sample": 1, "latency_p99_ms": 248.25, "up": 1.0, "latency_ok": true, "up_ok": true}
{"ts": "2026-06-18T03:09:16.247881Z", "level": "INFO", "event_type": "VERIFY_SAMPLE", "service": "payment-svc", "sample": 2, "latency_p99_ms": 248.1938775510204, "up": 1.0, "latency_ok": true, "up_ok": true}
{"ts": "2026-06-18T03:09:26.272657Z", "level": "INFO", "event_type": "VERIFY_SAMPLE", "service": "payment-svc", "sample": 3, "latency_p99_ms": 248.1865671641791, "up": 1.0, "latency_ok": true, "up_ok": true}
{"ts": "2026-06-18T03:09:26.273130Z", "level": "INFO", "event_type": "VERIFY_PASS", "service": "payment-svc", "samples": 3}
{"ts": "2026-06-18T03:09:26.275471Z", "level": "INFO", "event_type": "ACTION_SUCCESS", "alertname": "HighLatency", "service": "payment-svc", "runbook": "runbooks/restart_service.sh"}
```

**Đánh giá:** PASS. p99 latency giảm từ >500ms về mức an toàn ~248ms sau khi restart container (restart xóa bỏ cấu hình netem của `tc`). Cả 3 mẫu thử liên tục đạt yêu cầu giúp Verify thành công.

---

## 2. Scenario 2 — Action fail → rollback (checkout-svc bị stop)

**Cách thức thực hiện:**
1. Thiết lập tạm thời `latency_p99_max_ms: 1` trong `baseline.json` để ép bước Verify luôn luôn thất bại ngay cả khi dịch vụ khởi động lại thành công.
2. Dừng dịch vụ `checkout-svc` để kích hoạt cảnh báo:
   `bash data-pack/scripts/inject_fault.sh kill ronki-checkout-svc`

**Log orchestrator:**
```json
{"ts": "2026-06-18T03:16:17.240469Z", "level": "INFO", "event_type": "ALERT_DETECTED", "alertname": "InstanceDown", "service": "checkout-svc", "severity": "critical"}
{"ts": "2026-06-18T03:16:17.240784Z", "level": "INFO", "event_type": "DECIDE_RUNBOOK", "alertname": "InstanceDown", "service": "checkout-svc", "runbook": "runbooks/restart_service.sh"}
{"ts": "2026-06-18T03:16:17.241641Z", "level": "INFO", "event_type": "BLAST_RADIUS_OK", "service": "checkout-svc"}
{"ts": "2026-06-18T03:16:17.241938Z", "level": "INFO", "event_type": "RUNBOOK_EXEC", "script": "runbooks/restart_service.sh", "service": "checkout-svc", "dry_run": true}
{"ts": "2026-06-18T03:16:17.246432Z", "level": "INFO", "event_type": "RUNBOOK_RESULT", "script": "runbooks/restart_service.sh", "service": "checkout-svc", "returncode": 0, "stdout": "[DRY-RUN] would execute: docker restart ronki-checkout-svc", "stderr": ""}
{"ts": "2026-06-18T03:16:17.246660Z", "level": "INFO", "event_type": "DRY_RUN_PASS", "runbook": "runbooks/restart_service.sh", "service": "checkout-svc"}
{"ts": "2026-06-18T03:16:17.246858Z", "level": "INFO", "event_type": "RUNBOOK_EXEC", "script": "runbooks/restart_service.sh", "service": "checkout-svc", "dry_run": false}
{"ts": "2026-06-18T03:16:22.697424Z", "level": "INFO", "event_type": "RUNBOOK_RESULT", "script": "runbooks/restart_service.sh", "service": "checkout-svc", "returncode": 0, "stdout": "[restart_service] Restarting ronki-checkout-svc...\nronki-checkout-svc\n[restart_service] Waiting 5s for ronki-checkout-svc to come up...\n[restart_service] ronki-checkout-svc is running.", "stderr": ""}
{"ts": "2026-06-18T03:16:22.697858Z", "level": "INFO", "event_type": "ACTION_EXECUTED", "runbook": "runbooks/restart_service.sh", "service": "checkout-svc"}
{"ts": "2026-06-18T03:16:22.698843Z", "level": "INFO", "event_type": "VERIFY_START", "service": "checkout-svc", "timeout_s": 60}
{"ts": "2026-06-18T03:16:22.719566Z", "level": "INFO", "event_type": "VERIFY_SAMPLE", "service": "checkout-svc", "sample": 1, "latency_p99_ms": null, "up": 1.0, "latency_ok": false, "up_ok": true}
{"ts": "2026-06-18T03:16:32.736271Z", "level": "INFO", "event_type": "VERIFY_SAMPLE", "service": "checkout-svc", "sample": 2, "latency_p99_ms": null, "up": 1.0, "latency_ok": false, "up_ok": true}
{"ts": "2026-06-18T03:16:42.759491Z", "level": "INFO", "event_type": "VERIFY_SAMPLE", "service": "checkout-svc", "sample": 3, "latency_p99_ms": 248.5, "up": 1.0, "latency_ok": false, "up_ok": true}
{"ts": "2026-06-18T03:16:52.774137Z", "level": "INFO", "event_type": "VERIFY_SAMPLE", "service": "checkout-svc", "sample": 4, "latency_p99_ms": 248.50000000000003, "up": 1.0, "latency_ok": false, "up_ok": true}
{"ts": "2026-06-18T03:17:02.786830Z", "level": "INFO", "event_type": "VERIFY_SAMPLE", "service": "checkout-svc", "sample": 5, "latency_p99_ms": 248.4844724796269, "up": 1.0, "latency_ok": false, "up_ok": true}
{"ts": "2026-06-18T03:17:12.817193Z", "level": "INFO", "event_type": "VERIFY_SAMPLE", "service": "checkout-svc", "sample": 6, "latency_p99_ms": 248.47557026541028, "up": 1.0, "latency_ok": false, "up_ok": true}
{"ts": "2026-06-18T03:17:22.820434Z", "level": "WARNING", "event_type": "VERIFY_FAIL", "service": "checkout-svc", "samples": 6}
{"ts": "2026-06-18T03:17:22.820849Z", "level": "WARNING", "event_type": "ROLLBACK_TRIGGERED", "service": "checkout-svc", "rollback_runbook": "runbooks/restart_service.sh"}
{"ts": "2026-06-18T03:17:22.821128Z", "level": "INFO", "event_type": "RUNBOOK_EXEC", "script": "runbooks/restart_service.sh", "service": "checkout-svc", "dry_run": false}
{"ts": "2026-06-18T03:17:38.435342Z", "level": "INFO", "event_type": "RUNBOOK_RESULT", "script": "runbooks/restart_service.sh", "service": "checkout-svc", "returncode": 0, "stdout": "[restart_service] Restarting ronki-checkout-svc...\nronki-checkout-svc\n[restart_service] Waiting 5s for ronki-checkout-svc to come up...\n[restart_service] ronki-checkout-svc is running.", "stderr": ""}
{"ts": "2026-06-18T03:17:38.436577Z", "level": "INFO", "event_type": "ROLLBACK_EXECUTED", "service": "checkout-svc", "rollback_runbook": "runbooks/restart_service.sh"}
```

**Đánh giá:** PASS. Sau khi khởi động lại dịch vụ thành công, độ trễ thực tế đo được (~248ms) lớn hơn ngưỡng cài đặt cưỡng bức (1ms). Bước Verify thất bại hoàn toàn sau 60 giây và tự động kích hoạt tiến trình Rollback (`ROLLBACK_TRIGGERED`) khởi chạy script khôi phục.

---

## 3. Scenario 3 — Circuit breaker (3 consecutive failures)

**Cách thức thực hiện:**
1. Duy trì ngưỡng `latency_p99_max_ms: 1` để các hành động xử lý liên tiếp thất bại.
2. Gửi tiếp cảnh báo `HighErrorRate` cho `payment-svc` vào Alertmanager. Cảnh báo này cộng với các lỗi thất bại trước đó sẽ làm tăng số lần lỗi liên tiếp (`consecutive_failures`) lên chạm ngưỡng 3.

**Log orchestrator:**
```json
{"ts": "2026-06-18T03:18:08.441786Z", "level": "INFO", "event_type": "ALERT_DETECTED", "alertname": "HighErrorRate", "service": "payment-svc", "severity": "critical"}
{"ts": "2026-06-18T03:18:08.442049Z", "level": "INFO", "event_type": "DECIDE_RUNBOOK", "alertname": "HighErrorRate", "service": "payment-svc", "runbook": "runbooks/clear_cache.sh"}
{"ts": "2026-06-18T03:18:08.442216Z", "level": "INFO", "event_type": "BLAST_RADIUS_OK", "service": "payment-svc"}
{"ts": "2026-06-18T03:18:08.442412Z", "level": "INFO", "event_type": "RUNBOOK_EXEC", "script": "runbooks/clear_cache.sh", "service": "payment-svc", "dry_run": true}
{"ts": "2026-06-18T03:18:08.449827Z", "level": "INFO", "event_type": "RUNBOOK_RESULT", "script": "runbooks/clear_cache.sh", "service": "payment-svc", "returncode": 0, "stdout": "[DRY-RUN] would execute: docker kill --signal=SIGHUP ronki-payment-svc", "stderr": ""}
{"ts": "2026-06-18T03:18:08.450094Z", "level": "INFO", "event_type": "DRY_RUN_PASS", "runbook": "runbooks/clear_cache.sh", "service": "payment-svc"}
{"ts": "2026-06-18T03:18:08.450308Z", "level": "INFO", "event_type": "RUNBOOK_EXEC", "script": "runbooks/clear_cache.sh", "service": "payment-svc", "dry_run": false}
{"ts": "2026-06-18T03:18:08.582798Z", "level": "INFO", "event_type": "RUNBOOK_RESULT", "script": "runbooks/clear_cache.sh", "service": "payment-svc", "returncode": 0, "stdout": "[clear_cache] Sending SIGHUP to ronki-payment-svc to flush cache...\nronki-payment-svc\n[clear_cache] SIGHUP sent to ronki-payment-svc. Cache flush triggered.", "stderr": ""}
{"ts": "2026-06-18T03:18:08.583001Z", "level": "INFO", "event_type": "ACTION_EXECUTED", "runbook": "runbooks/clear_cache.sh", "service": "payment-svc"}
{"ts": "2026-06-18T03:18:08.583224Z", "level": "INFO", "event_type": "VERIFY_START", "service": "payment-svc", "timeout_s": 60}
{"ts": "2026-06-18T03:18:08.592420Z", "level": "INFO", "event_type": "VERIFY_SAMPLE", "service": "payment-svc", "sample": 1, "latency_p99_ms": 248.26136363636363, "up": 1.0, "latency_ok": false, "up_ok": true}
{"ts": "2026-06-18T03:18:18.615324Z", "level": "INFO", "event_type": "VERIFY_SAMPLE", "service": "payment-svc", "sample": 2, "latency_p99_ms": 248.21875, "up": 1.0, "latency_ok": false, "up_ok": true}
{"ts": "2026-06-18T03:18:28.622615Z", "level": "INFO", "event_type": "VERIFY_SAMPLE", "service": "payment-svc", "sample": 3, "latency_p99_ms": 248.2325581395349, "up": 1.0, "latency_ok": false, "up_ok": true}
{"ts": "2026-06-18T03:18:38.634427Z", "level": "INFO", "event_type": "VERIFY_SAMPLE", "service": "payment-svc", "sample": 4, "latency_p99_ms": 248.23046875, "up": 1.0, "latency_ok": false, "up_ok": true}
{"ts": "2026-06-18T03:18:48.642995Z", "level": "INFO", "event_type": "VERIFY_SAMPLE", "service": "payment-svc", "sample": 5, "latency_p99_ms": 248.20238095238093, "up": 1.0, "latency_ok": false, "up_ok": true}
{"ts": "2026-06-18T03:18:58.684775Z", "level": "INFO", "event_type": "VERIFY_SAMPLE", "service": "payment-svc", "sample": 6, "latency_p99_ms": 248.21653543307085, "up": 1.0, "latency_ok": false, "up_ok": true}
{"ts": "2026-06-18T03:19:08.685173Z", "level": "WARNING", "event_type": "VERIFY_FAIL", "service": "payment-svc", "samples": 6}
{"ts": "2026-06-18T03:19:08.685772Z", "level": "WARNING", "event_type": "ROLLBACK_TRIGGERED", "service": "payment-svc", "rollback_runbook": "runbooks/restart_service.sh"}
{"ts": "2026-06-18T03:19:08.686105Z", "level": "INFO", "event_type": "RUNBOOK_EXEC", "script": "runbooks/restart_service.sh", "service": "payment-svc", "dry_run": false}
{"ts": "2026-06-18T03:19:24.331351Z", "level": "INFO", "event_type": "RUNBOOK_RESULT", "script": "runbooks/restart_service.sh", "service": "payment-svc", "returncode": 0, "stdout": "[restart_service] Restarting ronki-payment-svc...\nronki-payment-svc\n[restart_service] Waiting 5s for ronki-payment-svc to come up...\n[restart_service] ronki-payment-svc is running.", "stderr": ""}
{"ts": "2026-06-18T03:19:24.331843Z", "level": "INFO", "event_type": "ROLLBACK_EXECUTED", "service": "payment-svc", "rollback_runbook": "runbooks/restart_service.sh"}
{"ts": "2026-06-18T03:19:24.332008Z", "level": "ERROR", "event_type": "CIRCUIT_BREAKER_HALT", "consecutive_failures": 3, "threshold": 3, "message": "Automation halted. Manual intervention required."}
```

**Đánh giá:** PASS. Sau thất bại liên tiếp thứ 3 (không vượt qua được verify post-action), cầu chì lập tức chuyển sang trạng thái hở (`CIRCUIT_OPEN`), kích hoạt sự kiện `CIRCUIT_BREAKER_HALT`. Các lần kiểm tra vòng lặp sau đó đều bị bỏ qua (polling suspended).

---

## 4. Acceptance test #4 — Multi-step transactional rollback

**Cách thức thực hiện:**
1. Khôi phục `latency_p99_max_ms: 500` trong `baseline.json`.
2. Sửa đổi tạm thời `runbooks/multi_step_deploy.sh` tại block bước C (`--step-c`) để lập tức `exit 1` nhằm giả lập lỗi khi re-enable traffic.
3. Khởi chạy lại orchestrator và gửi cảnh báo `MultiStepDeploy` cho `api-gateway` vào Alertmanager.

**Log orchestrator:**
```json
{"ts": "2026-06-18T03:22:48.951455Z", "level": "INFO", "event_type": "ALERT_DETECTED", "alertname": "MultiStepDeploy", "service": "api-gateway", "severity": "critical"}
{"ts": "2026-06-18T03:22:48.951669Z", "level": "INFO", "event_type": "DECIDE_RUNBOOK", "alertname": "MultiStepDeploy", "service": "api-gateway", "runbook": "runbooks/multi_step_deploy.sh"}
{"ts": "2026-06-18T03:22:48.951799Z", "level": "INFO", "event_type": "BLAST_RADIUS_OK", "service": "api-gateway"}
{"ts": "2026-06-18T03:22:48.951970Z", "level": "INFO", "event_type": "RUNBOOK_EXEC", "script": "runbooks/multi_step_deploy.sh", "service": "api-gateway", "dry_run": true}
{"ts": "2026-06-18T03:22:48.957231Z", "level": "INFO", "event_type": "RUNBOOK_RESULT", "script": "runbooks/multi_step_deploy.sh", "service": "api-gateway", "returncode": 0, "stdout": "[DRY-RUN] would execute: full 3-step deploy on ronki-api-gateway", "stderr": ""}
{"ts": "2026-06-18T03:22:48.958279Z", "level": "INFO", "event_type": "DRY_RUN_PASS", "runbook": "runbooks/multi_step_deploy.sh", "service": "api-gateway"}
{"ts": "2026-06-18T03:22:48.958546Z", "level": "INFO", "event_type": "RUNBOOK_EXEC", "script": "runbooks/multi_step_deploy.sh --step-a", "service": "api-gateway", "dry_run": false}
{"ts": "2026-06-18T03:22:48.994357Z", "level": "INFO", "event_type": "RUNBOOK_RESULT", "script": "runbooks/multi_step_deploy.sh --step-a", "service": "api-gateway", "returncode": 0, "stdout": "[multi_step_deploy] step-A: draining traffic from ronki-api-gateway...\nronki-api-gateway\n[multi_step_deploy] step-A complete.", "stderr": ""}
{"ts": "2026-06-18T03:22:48.994716Z", "level": "INFO", "event_type": "RUNBOOK_EXEC", "script": "runbooks/multi_step_deploy.sh --step-b", "service": "api-gateway", "dry_run": false}
{"ts": "2026-06-18T03:22:52.791679Z", "level": "INFO", "event_type": "RUNBOOK_RESULT", "script": "runbooks/multi_step_deploy.sh --step-b", "service": "api-gateway", "returncode": 0, "stdout": "[multi_step_deploy] step-B: applying new config to ronki-api-gateway...\nronki-api-gateway\n[multi_step_deploy] step-B complete.", "stderr": ""}
{"ts": "2026-06-18T03:22:52.791929Z", "level": "INFO", "event_type": "RUNBOOK_EXEC", "script": "runbooks/multi_step_deploy.sh --step-c", "service": "api-gateway", "dry_run": false}
{"ts": "2026-06-18T03:22:52.811944Z", "level": "INFO", "event_type": "RUNBOOK_RESULT", "script": "runbooks/multi_step_deploy.sh --step-c", "service": "api-gateway", "returncode": 1, "stdout": "[multi_step_deploy] step-C: re-enabling traffic for ronki-api-gateway...", "stderr": ""}
{"ts": "2026-06-18T03:22:52.812202Z", "level": "ERROR", "event_type": "TRANSACTIONAL_STEP_FAIL", "step": "runbooks/multi_step_deploy.sh --step-c", "service": "api-gateway", "completed_before_failure": ["runbooks/multi_step_deploy.sh --step-a", "runbooks/multi_step_deploy.sh --step-b"]}
{"ts": "2026-06-18T03:22:52.813246Z", "level": "WARNING", "event_type": "TRANSACTIONAL_ROLLBACK_STEP", "step": "runbooks/multi_step_deploy.sh --rollback-b", "service": "api-gateway"}
{"ts": "2026-06-18T03:22:52.813409Z", "level": "INFO", "event_type": "RUNBOOK_EXEC", "script": "runbooks/multi_step_deploy.sh --rollback-b", "service": "api-gateway", "dry_run": false}
{"ts": "2026-06-18T03:23:06.432151Z", "level": "INFO", "event_type": "RUNBOOK_RESULT", "script": "runbooks/multi_step_deploy.sh --rollback-b", "service": "api-gateway", "returncode": 0, "stdout": "[multi_step_deploy] rollback-B: reverting config on ronki-api-gateway...\nronki-api-gateway\n[multi_step_deploy] rollback-B complete.", "stderr": ""}
{"ts": "2026-06-18T03:23:06.432727Z", "level": "WARNING", "event_type": "TRANSACTIONAL_ROLLBACK_STEP", "step": "runbooks/multi_step_deploy.sh --rollback-a", "service": "api-gateway"}
{"ts": "2026-06-18T03:23:06.433142Z", "level": "INFO", "event_type": "RUNBOOK_EXEC", "script": "runbooks/multi_step_deploy.sh --rollback-a", "service": "api-gateway", "dry_run": false}
{"ts": "2026-06-18T03:23:08.517287Z", "level": "INFO", "event_type": "RUNBOOK_RESULT", "script": "runbooks/multi_step_deploy.sh --rollback-a", "service": "api-gateway", "returncode": 0, "stdout": "[multi_step_deploy] rollback-A: restoring traffic to ronki-api-gateway...\nronki-api-gateway\n[multi_step_deploy] rollback-A complete.", "stderr": ""}
{"ts": "2026-06-18T03:23:08.517891Z", "level": "INFO", "event_type": "TRANSACTIONAL_ROLLBACK_COMPLETE", "service": "api-gateway", "rolled_back": ["runbooks/multi_step_deploy.sh --rollback-b", "runbooks/multi_step_deploy.sh --rollback-a"]}
```

**Đánh giá:** PASS. Hệ thống đã log chính xác `TRANSACTIONAL_STEP_FAIL` cho thấy lỗi ở bước C và hai bước trước đó đã hoàn thành là bước A và bước B. Sau đó, tiến trình Rollback giao dịch được kích hoạt ngược thứ tự một cách chuẩn xác: `rollback-b` được chạy trước để khôi phục cấu hình, theo sau là `rollback-a` để đưa traffic trở lại. Sự kiện `TRANSACTIONAL_ROLLBACK_COMPLETE` liệt kê đầy đủ chuỗi hành động rollback đảo ngược.

---

## 5. Acceptance test #5 — Concurrent alert race

**Cách thức thực hiện:**
1. Khôi phục `multi_step_deploy.sh` về trạng thái nguyên bản.
2. Sử dụng API của Alertmanager để gửi đồng thời 3 cảnh báo trong cùng một thời điểm:
   - Alert 1: `HighLatency` trên `payment-svc`
   - Alert 2: `HighLatency` trên `inventory-svc`
   - Alert 3 (Cảnh báo trùng lặp): `HighLatency` trên `payment-svc` (được bổ sung thêm nhãn phân biệt `duplicate: true` để Alertmanager không gộp chung fingerprint).

**Log orchestrator:**
```json
{"ts": "2026-06-18T03:24:47.646919Z", "level": "INFO", "event_type": "ALERT_DETECTED", "alertname": "HighLatency", "service": "payment-svc", "severity": "warning"}
{"ts": "2026-06-18T03:24:47.647827Z", "level": "INFO", "event_type": "ALERT_DETECTED", "alertname": "HighLatency", "service": "payment-svc", "severity": "warning"}
{"ts": "2026-06-18T03:24:47.647264Z", "level": "INFO", "event_type": "ALERT_DETECTED", "alertname": "HighLatency", "service": "inventory-svc", "severity": "warning"}
{"ts": "2026-06-18T03:24:47.648355Z", "level": "INFO", "event_type": "DECIDE_RUNBOOK", "alertname": "HighLatency", "service": "inventory-svc", "runbook": "runbooks/restart_service.sh"}
{"ts": "2026-06-18T03:24:47.648629Z", "level": "INFO", "event_type": "DECIDE_RUNBOOK", "alertname": "HighLatency", "service": "payment-svc", "runbook": "runbooks/restart_service.sh"}
{"ts": "2026-06-18T03:24:47.648933Z", "level": "INFO", "event_type": "BLAST_RADIUS_OK", "service": "payment-svc"}
{"ts": "2026-06-18T03:24:47.649265Z", "level": "INFO", "event_type": "RUNBOOK_EXEC", "script": "runbooks/restart_service.sh", "service": "payment-svc", "dry_run": true}
{"ts": "2026-06-18T03:24:47.650922Z", "level": "INFO", "event_type": "DECIDE_RUNBOOK", "alertname": "HighLatency", "service": "payment-svc", "runbook": "runbooks/restart_service.sh"}
{"ts": "2026-06-18T03:24:47.653713Z", "level": "INFO", "event_type": "BLAST_RADIUS_OK", "service": "inventory-svc"}
{"ts": "2026-06-18T03:24:47.654091Z", "level": "INFO", "event_type": "RUNBOOK_EXEC", "script": "runbooks/restart_service.sh", "service": "inventory-svc", "dry_run": true}
{"ts": "2026-06-18T03:24:47.655845Z", "level": "INFO", "event_type": "BLAST_RADIUS_OK", "service": "payment-svc"}
{"ts": "2026-06-18T03:24:47.656178Z", "level": "WARNING", "event_type": "SERVICE_LOCK_BUSY", "service": "payment-svc", "message": "Another runbook is executing for this service; skipping duplicate"}
{"ts": "2026-06-18T03:24:47.656881Z", "level": "INFO", "event_type": "RUNBOOK_RESULT", "script": "runbooks/restart_service.sh", "service": "payment-svc", "returncode": 0, "stdout": "[DRY-RUN] would execute: docker restart ronki-payment-svc", "stderr": ""}
{"ts": "2026-06-18T03:24:47.657155Z", "level": "INFO", "event_type": "DRY_RUN_PASS", "runbook": "runbooks/restart_service.sh", "service": "payment-svc"}
{"ts": "2026-06-18T03:24:47.657423Z", "level": "INFO", "event_type": "RUNBOOK_EXEC", "script": "runbooks/restart_service.sh", "service": "payment-svc", "dry_run": false}
{"ts": "2026-06-18T03:24:47.666039Z", "level": "INFO", "event_type": "RUNBOOK_RESULT", "script": "runbooks/restart_service.sh", "service": "inventory-svc", "returncode": 0, "stdout": "[DRY-RUN] would execute: docker restart ronki-inventory-svc", "stderr": ""}
{"ts": "2026-06-18T03:24:47.666697Z", "level": "INFO", "event_type": "DRY_RUN_PASS", "runbook": "runbooks/restart_service.sh", "service": "inventory-svc"}
{"ts": "2026-06-18T03:24:47.667023Z", "level": "INFO", "event_type": "RUNBOOK_EXEC", "script": "runbooks/restart_service.sh", "service": "inventory-svc", "dry_run": false}
{"ts": "2026-06-18T03:25:23.504256Z", "level": "INFO", "event_type": "VERIFY_SAMPLE", "service": "inventory-svc", "sample": 3, "latency_p99_ms": 94.10714285714288, "up": 1.0, "latency_ok": true, "up_ok": true}
{"ts": "2026-06-18T03:25:23.504818Z", "level": "INFO", "event_type": "VERIFY_PASS", "service": "inventory-svc", "samples": 3}
{"ts": "2026-06-18T03:25:23.505410Z", "level": "INFO", "event_type": "ACTION_SUCCESS", "alertname": "HighLatency", "service": "inventory-svc", "runbook": "runbooks/restart_service.sh"}
{"ts": "2026-06-18T03:25:23.554104Z", "level": "INFO", "event_type": "VERIFY_SAMPLE", "service": "payment-svc", "sample": 3, "latency_p99_ms": 248.18918918918916, "up": 1.0, "latency_ok": true, "up_ok": true}
{"ts": "2026-06-18T03:25:23.554555Z", "level": "INFO", "event_type": "VERIFY_PAS
S", "service": "payment-svc", "samples": 3}
{"ts": "2026-06-18T03:25:23.555150Z", "level": "INFO", "event_type": "ACTION_SUC
CESS", "alertname": "HighLatency", "service": "payment-svc", "runbook": "runbook
s/restart_service.sh"}
```

**Đánh giá:** PASS. Hai dịch vụ khác nhau `payment-svc` và `inventory-svc` hoàn toàn chạy độc lập, song song và không chặn nhau (mốc thời gian chạy thử `dry-run` bắt đầu hoàn toàn trong cùng 1 giây `03:24:47`). Đồng thời, cảnh báo trùng lặp thứ hai cho `payment-svc` bị chặn lại và log lỗi `SERVICE_LOCK_BUSY` do khóa dịch vụ đang bị chiếm giữ bởi luồng đầu tiên.

---

## 6. Acceptance test #6 — LLM hallucination defense

**Cách thức thực hiện:**
1. Trong `config.yaml`, bổ sung cấu hình mapping giả lập cho một cảnh báo ảo:
   `TestHallucination: "runbooks/nonexistent_runbook.sh"`
2. Đảm bảo file kịch bản không tồn tại và không nằm trong cấu hình `runbook_registry`.
3. Gửi cảnh báo `TestHallucination` cho `payment-svc` vào Alertmanager.

**Log orchestrator:**
```json
{"ts": "2026-06-18T03:29:02.752755Z", "level": "INFO", "event_type": "ALERT_DETE
CTED", "alertname": "TestHallucination", "service": "payment-svc", "severity": "
warning"}
{"ts": "2026-06-18T03:29:02.753109Z", "level": "ERROR", "event_type": "DECISION_
VALIDATION_FAILED", "bad_runbook": "runbooks/nonexistent_runbook.sh", "alertname
": "TestHallucination", "raw_decision": "runbooks/nonexistent_runbook.sh", "acti
on": "escalate_no_auto_action"}
```

**Đánh giá:** PASS. Orchestrator chặn đứng việc thực thi kịch bản ảo ngay lập tức. Log chính xác sự kiện `DECISION_VALIDATION_FAILED` chứa đầy đủ 4 trường thông tin. Không có tiến trình con nào được kích hoạt, cầu chì không tăng số lỗi thất bại.
