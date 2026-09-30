# Alert và Runbook

Các ngưỡng alert đồng bộ với `config/slo.yaml` và `config/dashboard.yaml`. Mỗi alert được gửi tới Slack `#k4-l3b-alerts`; thay channel này bằng channel được lớp cấp nếu khác. Owner bài lab: `student-2A202602528`.

## Alert 1

- **Tên:** `HighLatencyP95`
- **Severity/duration:** warning trong 5 phút liên tục.
- **Điều kiện:** P95 `response_sent.latency_ms` lớn hơn 3000 ms.
- **Ảnh hưởng:** người dùng chờ lâu hơn trước khi nhận câu trả lời.
- **Kiểm tra:**
  1. Xác nhận P95/P99 và TTFT trên dashboard trong time range bị cảnh báo.
  2. Lọc `data/logs.jsonl` theo thời gian và chọn request có `latency_ms` cao.
  3. Mở trace khớp `correlation_id`, so sánh span retrieval và generation.
- **Mitigation:** nếu evidence cho thấy retrieval chậm, khôi phục trạng thái retrieval đã biết tốt; nếu generation/prompt gây chậm, rollback label `production` về version tốt gần nhất. Chạy lại workload để xác nhận P95 hồi phục.

## Alert 2

- **Tên:** `HighRequestErrorRate`
- **Severity/duration:** critical trong 5 phút liên tục.
- **Điều kiện:** tỷ lệ `request_failed / request_received` lớn hơn 2%.
- **Ảnh hưởng:** một phần request không nhận được câu trả lời.
- **Kiểm tra:**
  1. Xác nhận error rate và phân loại `error_type` trên dashboard/log.
  2. Lấy một `correlation_id` lỗi và kiểm tra event `request_failed` tương ứng.
  3. Mở trace cùng ID để xác định observation nào lỗi; kiểm tra phạm vi ảnh hưởng.
- **Mitigation:** khôi phục dependency/config vừa thay đổi nếu có bằng chứng liên quan; nếu đang chạy practice scenario, tắt đúng scenario. Chỉ đóng alert sau khi request mới thành công và error rate giảm dưới ngưỡng.

## Alert 3

- **Tên:** `LowRetrievalSuccess`
- **Severity/duration:** warning trong 10 phút liên tục.
- **Điều kiện:** tỷ lệ `tool_success` của retrieval thấp hơn 90%.
- **Ảnh hưởng:** câu trả lời có thể thiếu ngữ cảnh hoặc request bị lỗi retrieval.
- **Kiểm tra:**
  1. So sánh retrieval success với error rate và feature bị ảnh hưởng.
  2. Lọc log theo `tool_name=retrieval`, `tool_success=false` và lấy correlation ID.
  3. Kiểm tra trace/span retrieval tương ứng và log lỗi dependency.
- **Mitigation:** khôi phục vector store/dependency hoặc cấu hình truy vấn đã biết tốt; không tắt retrieval âm thầm. Kiểm chứng retrieval success trở lại ít nhất 90% trên workload mới.
