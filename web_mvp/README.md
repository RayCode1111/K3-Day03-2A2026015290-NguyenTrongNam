# Lab 03 Web MVP

MVP này bọc lại các tính năng chính của lab trong một trang web đơn giản:

- Chatbot baseline: một LLM call, không gọi tool.
- ReAct Agent V2: vòng lặp Thought -> Action -> Observation, dùng tool registry của lab.
- Tool e-commerce: `check_stock`, `get_discount`, `calc_shipping`.
- API key được đọc từ file `.env` ở thư mục gốc repo, không đưa xuống frontend.

## Cấu hình

Ở thư mục gốc repo, file `.env` cần có API key thật:

```env
DEFAULT_PROVIDER=openai
DEFAULT_MODEL=gpt-4o
OPENAI_API_KEY=sk-...
```

Hoặc dùng Gemini:

```env
DEFAULT_PROVIDER=gemini
DEFAULT_MODEL=gemini-3.6-flash
GEMINI_API_KEY=...
```

## Chạy

Từ thư mục gốc repo:

```bash
python web_mvp/app.py
```

Nếu máy Windows dùng Python launcher:

```bash
py web_mvp/app.py
```

Sau đó mở:

```text
http://127.0.0.1:5000
```

Có thể đổi port:

```bash
set MVP_PORT=5050
python web_mvp/app.py
```

## Ghi chú môi trường

App không cần Flask hay web framework khác. Nó dùng `http.server` của Python để tránh thêm dependency. Phần gọi model vẫn cần các dependency của lab như `openai`, `google-genai`, `python-dotenv`.
