# Báo cáo cá nhân: Lab 03 - Chatbot vs ReAct Agent

- **Họ và tên**: Nguyễn Trọng Nam
- **MSSV**: 2A202601529
- **Ngày**: 2026-07-28

---

## I. Đóng góp kỹ thuật (15 điểm)

Trong bài lab này, em phụ trách các thành phần cốt lõi để xây dựng và so sánh giữa chatbot baseline và ReAct Agent. Mục tiêu chính là làm rõ khi nào chatbot thông thường không đủ, và vì sao cần agent có khả năng gọi tool để lấy dữ liệu thật.

- **Contribution tổng quan**: Hoàn thiện chatbot baseline, bổ tool deterministic, ReAct loop, cơ chế recovery cho Agent V2, artifact đánh giá và web MVP để demo bài lab bằng API key.
- **Module đã thực hiện**: `src/chatbot/chatbot.py`, `src/tools/tools.py`, `src/agent/agent.py`, `src/agent/agent_v2.py`, `web_mvp/app.py`
- **Technical contribution**: Xây dựng system prompt cho chatbot theo hướng không được bịa dữ liệu; thiết kế parser `parse_action`; tạo tool registry cho `check_stock`, `get_discount`, `calc_shipping`; chèn `Observation` vào transcript để agent tiếp tục lập luận; bổ sung repeated-action guard trong Agent V2; đóng gói luồng chạy thành giao diện web để so sánh chatbot và agent trên cùng một câu hỏi.
- **Tài liệu hoá và artifact**: Tạo test cho chatbot/tool/agent, lưu trace thành công và failed trace, sinh artifact đánh giá trong `artifacts/evaluation/lab_evaluation_results.json`.

## II. Phân tích một ca debug tiêu biểu (10 điểm)

- **Mô tả vấn đề**: Agent V1 có thể lặp lại cùng một tool call nhiều lần khi model không biết phải tiến tiếp như thế nào sau khi nhận observation.
- **Nguồn phát hiện**: Failed trace trong `artifacts/traces/failed_trace_repeated_action.json`.
- **Chẩn đoán**: Vòng lặp ReAct ở phiên bản đầu có `max_steps` và xử lý parse error, nhưng chưa có cơ chế chặn khi model lặp lại đúng cùng `Action` và cùng `args`. Điều này làm agent tốn step budget nhưng không tạo ra thêm bằng chứng mới.
- **Cách khắc phục**: Tạo `ReActAgentV2` trong `src/agent/agent_v2.py`, thêm repeated-action guard dựa trên cặp `(tool_name, args)`. Nếu action mới giống hệt action trước đó, agent dừng sớm và trả về fallback an toàn thay vì tiếp tục loop.
- **Kết quả sau khi sửa**: Agent V2 kết thúc ổn định hơn trong các tình huống model bị kẹt, dễ debug hơn, và tránh trả lời như thể đã xử lý được dữ liệu trong khi thực tế không có thông tin mới.

## III. Nhận xét cá nhân: Chatbot và ReAct Agent (10 điểm)

1. **Chatbot phù hợp với câu hỏi tính và câu hỏi tổng quát**: Với những câu hỏi như chính sách đổi trả hoặc giờ làm việc, chatbot baseline nhanh, đơn giản, chi phí thấp, không cần orchestration.
2. **Agent mạnh hơn khi bài toán cần dữ liệu thật và nhiều bước**: Khi người dùng hỏi tổng tiền, mã giảm giá, tồn kho, phí vận chuyển, chatbot dễ bị hallucination hoặc phải fallback. Agent có thể gọi tool để lấy evidence rồi mới đưa ra kết luận.
3. **Observation là điểm khác biệt lớn nhất**: Trong agent, kết quả tool không do model tự bịa ra mà do application chèn lại vào transcript. Nhờ đó câu trả lời grounded hơn và có thể truy vết.
4. **Guard rail là phần quan trọng để đưa agent vào demo thực tế**: Không chỉ cần agent gọi được tool, mà còn cần agent dừng đúng lúc khi gặp parse error, unknown tool, invalid arguments hoặc repeated action.

## IV. Kết quả đã đạt được (5 điểm)

Dưới artifact đánh giá trong `artifacts/evaluation/lab_evaluation_results.json`, kết quả tổng hợp của submission hiện tại như sau:

- **Agent success rate**: `1.0` trên 5 test case.
- **Chatbot safe fallback rate**: `0.6`.
- **Agent average steps**: `2.4`.
- **Case multi-step tiêu biểu**: Agent gọi theo chuỗi `check_stock -> get_discount -> calc_shipping -> Final Answer` cho bài toán mua 2 iPhone đúng mã `WINNER` và giao tới Hà Nội.

Nhận xét ngắn: chatbot baseline thể hiện đúng vai trò "đường cơ sở" để so sánh, trong khi agent cho thấy giá trị rõ ràng khi cần xử lý câu hỏi cần evidence và tính toán nhiều bước.

## V. Hướng cải tiến tiếp theo (5 điểm)

- **Mở rộng phạm vi tool**: Thêm tool tính đơn hàng nhiều sản phẩm, nhiều điểm giao, và xử lý quantity phức tạp hơn.
- **Router cho out-of-scope**: Thêm lớp nhận biết câu hỏi ngoài domain e-commerce để agent có thể từ chối lịch sự và thống nhất hơn.
- **Ổn định ngôn ngữ trả lời**: Bổ sung chính sách trả lời cùng ngôn ngữ với người dùng để chatbot và agent đồng nhất hơn khi demo.
- **Hoàn thiện web demo**: Thêm chọn provider trên giao diện, thêm hiển thị telemetry và so sánh chi phí giữa chatbot và agent.

---