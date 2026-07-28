# Báo cáo nhóm: Lab 3 - Chatbot so với ReAct Agent

- **Tên nhóm**: IDK
- **Thành viên**: Nguyễn Trọng Nam, Lê Việt Hoàng
- **Ngày triển khai**: 28/07/2026

---

## 1. Tóm tắt điều hành

Lab này so sánh chatbot baseline với ReAct agent trên 5 tình huống kiểm thử. Kết quả chính: chatbot phù hợp hơn với các câu hỏi mang tính thông tin đơn giản, trong khi agent thể hiện rõ hiệu quả hơn trong các bài toán nhiều bước cần sử dụng công cụ và bằng chứng từ hệ thống.

- **Tỷ lệ thành công**: 5/5 cho agent trong đánh giá deterministic
- **Kết quả nổi bật**: Agent sử dụng đúng chuỗi check_stock -> get_discount -> calc_shipping khi bài toán cần nhiều bước; chatbot baseline chỉ trả lời an toàn nhưng thiếu bằng chứng từ công cụ

---

## 2. Kiến trúc hệ thống và công cụ

### 2.1 Triển khai vòng lặp ReAct
Tệp src/agent/agent.py triển khai chuỗi Thought -> Action -> Observation -> Final Answer, kèm các tham số max_steps, parser, executor và cơ chế fallback có cấu trúc. Phiên bản V2 trong src/agent/agent_v2.py bổ sung cơ chế phát hiện hành động lặp lại.

### 2.2 Các định nghĩa công cụ (hệ thống tồn kho)
| Tên công cụ | Định dạng đầu vào | Mục đích sử dụng |
| :--- | :--- | :--- |
| check_stock | {"item_name": "iPhone"} | Tra giá, tồn kho và trọng lượng |
| get_discount | {"coupon_code": "WINNER"} | Kiểm tra mã giảm giá |
| calc_shipping | {"weight": 0.8, "destination": "Hanoi"} | Tính phí vận chuyển và số ngày |

### 2.3 Nhà cung cấp LLM được sử dụng
- **Primary**: OpenAI (src/core/openai_provider.py)
- **Secondary (Backup)**: Gemini và local provider có sẵn trong repo, nhưng đánh giá deterministic không cần gọi thật

---

## 3. Telemetry và bảng điều khiển hiệu năng

- **Nguồn số liệu deterministic**: `artifacts/evaluation/lab_evaluation_results.json`, sinh từ `scripts/run_lab_evaluation.py`.
- **Nguồn số liệu real-model**: lần chạy thủ công ngày `28/07/2026` với `OpenAI gpt-4o-2024-08-06`, dùng đúng prompt ReAct và tool registry của workspace cho case `2 iPhone + WINNER + ship Hanoi`.
- **Độ trễ trung vị (P50)**: `1187 ms` trên 4 lượt gọi LLM của case real-model.
- **Độ trễ gần cực đại (P99, xấp xỉ theo mẫu nhỏ)**: `1417 ms` trên cùng case. Vì chỉ có 4 lượt gọi nên đây là ước lượng theo mẫu nhỏ, chưa phải benchmark production quy mô lớn.
- **Số token mỗi tác vụ**: `1412 total tokens/task` gồm `1201 prompt tokens` và `211 completion tokens`.
- **Tổng chi phí cho deterministic suite**: `0` vì không gọi API trả phí.
- **Tổng chi phí cho lần chạy real-model mẫu**: có phát sinh chi phí API OpenAI, nhưng repo hiện chưa cài công thức pricing thật trong `src/telemetry/metrics.py`, nên chưa quy đổi chính xác sang USD/VND trong báo cáo.
- **Số bước trung bình của agent trong deterministic suite**: `2.4 bước/tác vụ` trên 5 case.
- **Tỷ lệ thành công của agent trong deterministic suite**: `5/5 case = 100%`.
- **Tỷ lệ safe fallback của chatbot baseline trong deterministic suite**: `3/5 case = 60%`, chủ yếu ở các bài toán cần công cụ nhiều bước.

---

## 4. Phân tích nguyên nhân gốc rễ (RCA) – các trace lỗi

### Câu chuyện điển hình: Hành động lặp lại
- **Đầu vào**: `Repeated action failure case`, được lưu trong `artifacts/traces/failed_trace_repeated_action.json`.
- **Quan sát**: V1 có thể gọi lại `check_stock({"item_name": "iPhone"})` với cùng tham số. Trace lỗi ghi nhận bước 1 trả về `ok`, bước 2 lặp lại cùng tool/args và bị đánh dấu `repeated_action`.
- **Nguyên nhân gốc rễ**: `src/agent/agent.py` chỉ giới hạn bằng `max_steps`; nếu LLM tiếp tục phát cùng Action thì agent vẫn chạy đến hết ngân sách bước thay vì nhận biết vòng lặp sớm.
- **Tác động**: Tốn bước, làm trace dài không cần thiết, tăng nguy cơ phát sinh chi phí khi dùng provider thật và làm phản hồi cuối kém rõ ràng.
- **Cách khắc phục**: `src/agent/agent_v2.py` tạo `action_key = (tool_name, json.dumps(args, sort_keys=True))` và so với action trước đó. Nếu trùng, V2 dừng ngay với fallback: `I stopped because the same tool call repeated without new evidence.`

---

## 5. Nghiên cứu ablation và thực nghiệm

### Thí nghiệm 1: Agent V1 so với V2
- **Sự khác biệt**: V2 bổ sung bộ phát hiện hành động lặp lại, còn V1 chỉ có `max_steps`.
- **Thiết lập**: Cùng một lỗi mô phỏng: agent gọi `check_stock({"item_name": "iPhone"})` lặp lại.
- **Kết quả V1**: Tiếp tục cho đến khi hết ngân sách bước hoặc nhận được final answer từ LLM.
- **Kết quả V2**: Dừng ở bước lặp đầu tiên, ghi observation `{"ok": false, "error": "repeated_action"}` và trả fallback an toàn.
- **Kết luận**: V2 tốt hơn cho môi trường production vì giảm vòng lặp, giảm chi phí tiềm năng và giúp trace lỗi dễ phân tích hơn.

### Thí nghiệm 2 (Bonus): Chatbot so với Agent
| Trường hợp | Kết quả chatbot | Kết quả agent | Người thắng |
| :--- | :--- | :--- | :--- |
| Case 1: Return policy | Đúng | Đúng | Hòa |
| Case 2: Working hours | Đúng | Đúng | Hòa |
| Case 3: 2 iPhone + WINNER + ship Hanoi | Safe fallback | Đúng, gọi `check_stock -> get_discount -> calc_shipping` | **Agent** |
| Case 4: MacBook ship Saigon | Safe fallback | Đúng, phát hiện hết hàng qua `check_stock` | **Agent** |
| Case 5: iPad + LEGACY + ship Saigon | Safe fallback | Đúng, xử lý mã hết hạn và phí ship | **Agent** |

Kết quả tổng hợp: agent đạt 100% success rate trong 5/5 case; chatbot baseline đúng ở 2 case đơn giản và fallback an toàn ở 3 case nhiều bước.

### Thí nghiệm 3: Chạy thử với model thật
- **Mô hình**: `gpt-4o-2024-08-06`
- **Bài toán**: `I want to buy 2 iPhones using code 'WINNER' and ship to Hanoi. The package weight is 0.8 kg. Total?`
- **Số lượt gọi LLM**: `4`
- **Độ trễ từng lượt**: `1417 ms`, `1187 ms`, `1181 ms`, `1315 ms`
- **Tổng token**: `1412`
- **Kết quả**: Agent đi đúng chuỗi công cụ `check_stock -> get_discount -> calc_shipping` và trả đúng tổng tiền `45,038,000 VND`
---

## 6. Đánh giá sẵn sàng cho sản xuất

- **Bảo mật**: Đã tránh commit khóa API và dữ liệu PII; các file `.env` và `logs` nằm trong `.gitignore`.
- **Tường lửa an toàn**: Có `max_steps`, xử lý lỗi có cấu trúc (`parse_error`, `missing_action`, `unknown_tool`, `invalid_arguments`) và cơ chế ngăn hành động lặp lại ở V2.
- **Độ tin cậy**: Deterministic suite đạt 5/5 case, trong đó case nhiều bước có trace thành công rõ ràng tại `artifacts/traces/success_trace_case_3.json`.
- **Quan sát hệ thống**: Logger đã ghi sự kiện `AGENT_START`, `AGENT_END`, `AGENT_V2_START`; nên bổ sung metric wall-clock latency, token usage và cost thật khi dùng API production.
- **Mở rộng**: Có thể mở rộng tool registry, thêm router/supervisor, thêm policy chọn công cụ và bổ sung test cho các lỗi như repeated action, tool không tồn tại, tham số sai.
- **Kết luận**: Sẵn sàng ở mức lab/demo deterministic; trước production thật cần bật telemetry đầy đủ, chạy kiểm thử với provider thật trong môi trường staging và đặt giới hạn chi phí/token theo request.

---

