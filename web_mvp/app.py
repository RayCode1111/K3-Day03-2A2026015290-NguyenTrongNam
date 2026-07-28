from __future__ import annotations

import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Tuple


ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = Path(__file__).resolve().parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _load_dotenv() -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def _json_bytes(payload: Dict[str, Any], status: int = 200) -> Tuple[int, bytes]:
    return status, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def _provider_from_env():
    provider = os.getenv("DEFAULT_PROVIDER", "openai").strip().lower()
    model = os.getenv("DEFAULT_MODEL", "gpt-4o").strip()

    if provider == "openai":
        from src.core.openai_provider import OpenAIProvider

        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_ADMIN_KEY")
        if not api_key or "your_" in api_key.lower():
            raise RuntimeError("Thiếu OPENAI_API_KEY hợp lệ trong file .env.")
        return OpenAIProvider(model_name=model, api_key=api_key), provider, model

    if provider in {"google", "gemini"}:
        from src.core.gemini_provider import GeminiProvider

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or "your_" in api_key.lower():
            raise RuntimeError("Thiếu GEMINI_API_KEY hợp lệ trong file .env.")
        return GeminiProvider(model_name=model, api_key=api_key), "gemini", model

    raise RuntimeError("MVP chỉ hỗ trợ DEFAULT_PROVIDER=openai hoặc gemini khi dùng API key.")


def _run_chatbot(question: str) -> Dict[str, Any]:
    from src.chatbot.chatbot import ChatbotBaseline

    llm, provider, model = _provider_from_env()
    bot = ChatbotBaseline(llm=llm)
    answer = bot.run(question)
    return {
        "ok": True,
        "mode": "chatbot",
        "provider": provider,
        "model": model,
        "answer": answer,
        "metrics": {
            "llm_calls": bot.llm_calls,
            "tool_calls": bot.tool_calls,
            "steps": 1,
            "classification": bot.classify_output(question, answer),
        },
        "trace": [],
    }


def _run_agent(question: str) -> Dict[str, Any]:
    from src.agent.agent_v2 import ReActAgentV2
    from src.tools.tools import get_tool_registry

    llm, provider, model = _provider_from_env()
    agent = ReActAgentV2(llm=llm, tools=get_tool_registry(), max_steps=6)
    answer = agent.run(question)
    tool_calls = sum(1 for step in agent.trace if step.get("action"))
    return {
        "ok": True,
        "mode": "agent",
        "provider": provider,
        "model": model,
        "answer": answer,
        "metrics": {
            "llm_calls": len(agent.trace),
            "tool_calls": tool_calls,
            "steps": len(agent.trace),
            "repeated_actions": getattr(agent, "repeated_actions", 0),
        },
        "trace": agent.trace,
    }


def _tools_payload() -> Dict[str, Any]:
    from src.tools.tools import CATALOG, COUPONS, SHIPPING_BY_DESTINATION, get_tool_registry

    tools = get_tool_registry()
    return {
        "ok": True,
        "tools": [
            {"name": tool["name"], "description": tool["description"]}
            for tool in tools.values()
        ],
        "sample_data": {
            "catalog": CATALOG,
            "coupons": COUPONS,
            "shipping_destinations": sorted(SHIPPING_BY_DESTINATION),
        },
    }


class MVPHandler(BaseHTTPRequestHandler):
    server_version = "LabMVP/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self._send_file(WEB_DIR / "templates" / "index.html", "text/html; charset=utf-8")
            return

        if self.path == "/api/tools":
            self._send_json_safe(lambda: _tools_payload())
            return

        if self.path.startswith("/static/"):
            relative = self.path.removeprefix("/static/").split("?", 1)[0]
            target = (WEB_DIR / "static" / relative).resolve()
            static_root = (WEB_DIR / "static").resolve()
            if static_root in target.parents and target.exists() and target.is_file():
                content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                self._send_file(target, content_type)
                return

        self._send_json({"ok": False, "error": "not_found"}, 404)

    def do_POST(self) -> None:
        if self.path not in {"/api/chatbot", "/api/agent"}:
            self._send_json({"ok": False, "error": "not_found"}, 404)
            return

        try:
            payload = self._read_json()
            question = str(payload.get("question", "")).strip()
            if not question:
                self._send_json({"ok": False, "error": "question_required"}, 400)
                return

            if self.path == "/api/chatbot":
                self._send_json_safe(lambda: _run_chatbot(question))
            else:
                self._send_json_safe(lambda: _run_agent(question))
        except json.JSONDecodeError:
            self._send_json({"ok": False, "error": "invalid_json"}, 400)

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("content-length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        return json.loads(body or "{}")

    def _send_json_safe(self, fn) -> None:
        try:
            self._send_json(fn())
        except Exception as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": "runtime_error",
                    "message": str(exc),
                },
                500,
            )

    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        status, body = _json_bytes(payload, status)
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    host = os.getenv("MVP_HOST", "127.0.0.1")
    port = int(os.getenv("MVP_PORT", "5000"))
    server = ThreadingHTTPServer((host, port), MVPHandler)
    print(f"Lab MVP is running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
