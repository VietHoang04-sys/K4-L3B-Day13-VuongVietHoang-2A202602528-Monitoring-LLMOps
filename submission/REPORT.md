# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Vương Việt Hoàng
- **MSSV:** 2A202602528
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/VietHoang04-sys/K4-L3B-Day13-VuongVietHoang-2A202602528-Monitoring-LLMOps
- **Commit SHA cuối:** Cập nhật sau khi commit/push phiên bản nộp.
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602528`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.txt` |
| Structured log | `evidence/04-structured-log.txt` |
| PII redaction | `evidence/05-pii-redaction.txt` |
| Trace list | `evidence/06-trace-list.png`, `evidence/06-trace-list.txt` |
| Trace waterfall | `evidence/07-trace-waterfall.png`, `evidence/07-trace-waterfall.txt` |
| Trace metadata | `evidence/08-trace-metadata.txt` |
| Prompt versions | `evidence/09-prompt-versions.png`, `evidence/09-prompt-versions.txt` |
| Prompt rollback | `evidence/10-prompt-rollback.png`, `evidence/10-prompt-rollback.txt` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.txt` |
| Incident log | `evidence/13-incident-log.txt` |
| Incident trace | `evidence/14-incident-trace.png`, `evidence/14-incident-trace.txt` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | Chưa có `data/logs.jsonl` | 100/100 | 0 thiếu field/context, 0 PII leak trên 75 records |
| `validate_dashboard.py` | 6/6 | 6/6 | Contract có đủ sáu panel |
| `pytest` | Thiếu `structlog`/`langfuse` trong môi trường ban đầu | 27 passed | Dependencies đã được cài từ manifest; chạy lại trên commit cuối |
| Số traces hợp lệ | Chưa có prompt managed | 19 | 19 root traces / 57 observations trong project cá nhân |
| Số PII leak | Chưa chạy | 0 | Validator quét 75 structured log records |
| Challenge latency P95 / TTFT P95 | Chưa đo | 3574 ms / 50 ms | Năm request challenge; xem `evidence/12-incident-metric.txt` |
| Challenge retrieval success rate | Chưa đo | 100% | 5/5 request challenge retrieval thành công |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware chấp nhận ID đúng mẫu `req-<8-hex>`, nếu không hợp lệ sẽ tạo ID mới; ID được bind vào structlog contextvars và trả trong `x-request-id`.
- **Các metadata được ghi vào structured log:** `user_id_hash`, `session_id`, `feature`, `model`, `env`, timestamp, event, latency/token/cost/quality khi đã có kết quả.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor xử lý chuỗi đệ quy sau khi format exception/stack và trước file writer/JSON renderer; hỗ trợ email, điện thoại Việt Nam, CCCD và thẻ thanh toán.
- **Cách kiểm chứng kết quả:** `validate_logs.py` đạt 100/100, 0 field/context thiếu và 0 PII leak trên 75 records; tests kiểm tra email, điện thoại, CCCD, thẻ và nested fields.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Dùng API observations v2 trên project `day13-k4-l3b-2A202602528`; xác nhận 19 root traces/57 observations trong 2 giờ gần nhất.
- **Cấu trúc root/retrieval/generation observations:** Root `lab-agent-run` có hai child: `retrieval` (retriever) và `llm-generation` (generation). Generation ghi model `claude-sonnet-4-5`, token usage và cost.
- **Cách nối trace với log:** `correlation_id` xuất hiện đồng nhất ở root observation và structured log; evidence waterfall/metadata gồm ID thật từ API v2.
- **Prompt name:** `day13-chat`.
- **Version/label baseline:** Version 1, labels `baseline` và `production`.
- **Version/label candidate:** Version 2, label `candidate`; sau rollback hiện có labels `candidate` và `latest`.
- **Trace ID của mỗi version:** baseline v1 `8a41674c220840553504a6385fdf8ad5`; candidate v2 `c1c92382bb2e3ac87d865b3dc1859eee`; production v2 sau promote `37c9cbe362062ef456731198668db3b4`; production v1 sau rollback `96547e136cdbd11a5e5beb0690c92379`.
- **Cách promote và rollback `production`:** Dùng Langfuse SDK `update_prompt`: chuyển `production` sang v2, tạo trace, trả label về v1 rồi tạo trace xác minh.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** `scripts/dashboard.py` cung cấp latency/TTFT, traffic, errors/retrieval success, cost, tokens và quality từ JSONL; contract validator đạt 6/6.
- **SLO và lý do chọn:** 99.5% request thành công trong tối đa 3000 ms trong cửa sổ 28 ngày, ưu tiên độ tin cậy và tail latency.
- **Cách tính error budget:** 100% - 99.5% = 0.5%; với 10,000 request, tối đa 50 request được phép không đạt SLO.
- **Ba alert và runbook tương ứng:** P95 latency >3000 ms/5 phút, request error rate >2%/5 phút, retrieval success <90%/10 phút; cấu hình trong `config/alert_rules.yaml`, hướng dẫn trong `docs/alerts.md`.

> Ví dụ cách viết error budget: "SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO."

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** 2026-09-30 12:40:50–12:41:04 UTC.
- **Triệu chứng từ metrics:** Năm request challenge có P95 latency 3574 ms, vượt challenge threshold 2000 ms; TTFT P95 là 50 ms. Retrieval success là 5/5.
- **Log line và correlation ID liên quan:** `req-536d1892` (3574 ms), `req-a3d8a4df` (2655 ms), `req-2b8ecb36` (2656 ms), `req-2f7850e2` (2656 ms), `req-bbe06e56` (2652 ms).
- **Trace ID và span gây ảnh hưởng:** Trace `d23c8e6e97d36d996ffebb872a3fed89` cùng correlation ID `req-536d1892`; root `lab-agent-run` 3576 ms, child retrieval `08ec80b892d27a1e` 2504 ms, generation `04d62d068e645260` 151 ms.
- **Root cause:** Practice challenge bật `rag_slow`; trace xác nhận retrieval mất khoảng 2.5 giây, vượt ngưỡng challenge 2 giây và chiếm phần lớn latency. Generation chỉ mất khoảng 151 ms.
- **Fix action:** Tắt `rag_slow` sau khi lấy evidence; xác nhận API không còn incident đang bật.
- **Preventive measure:** Giữ alert P95 latency, theo dõi duration retrieval và dùng correlation ID để mở span; áp dụng mitigation/rollback dựa trên span có duration bất thường.

> Gợi ý cách viết ngắn, không thay cho evidence thực tế: "Metric cho thấy `[latency/error/cost/quality]` bất thường trong `[khoảng thời gian]`. Log line `[event]` có `correlation_id=[...]` đại diện cho request bị ảnh hưởng. Trace cùng `correlation_id` cho thấy span `[retrieval/generation/prompt/tool]` có dấu hiệu `[chậm/lỗi/token tăng]`. Root cause là `[nguyên nhân suy ra từ evidence]`. Fix action là `[hành động khôi phục]`; preventive measure là `[alert/runbook/test/guardrail để ngăn tái diễn]`."

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Scrub sau khi render exception/stack nhưng trước JSON/file writer, để PII không lọt qua những trường ngoài `payload`.
- **Một lỗi/blocker đã gặp:** Langfuse API legacy `GET /api/public/traces` không còn hỗ trợ cho organization mới (HTTP 410); lúc đầu prompt `day13-chat` chưa tồn tại.
- **Cách tìm nguyên nhân và xử lý:** Chuyển sang Langfuse Python SDK v4 `api.observations.get_many(fields="core,basic,metadata,usage")`, tạo prompt v1/v2 và xác minh traces/span tree thành công.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics khoanh vùng thời gian/symptom, correlation ID tìm request trong log, trace phân rã thời gian theo span để xác nhận root cause.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Prompt version liên kết thay đổi chất lượng/latency/cost với request; SLO đặt ngưỡng vận hành và error budget định lượng mức suy giảm có thể chấp nhận.
- **Điều quan trọng nhất đã học:** Không kết luận nguyên nhân chỉ từ metric; cần nối cùng request qua log và trace.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Trace metadata được lưu ở dạng text; không chụp tab Data vì UI có thể hiển thị `scope.attributes.public_key`. Cập nhật commit SHA sau khi tạo commit cuối. Ảnh waterfall, prompt versions, rollback và incident trace trong project cá nhân đã được lưu.

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả evidence hiện có mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
