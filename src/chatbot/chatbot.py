from typing import Any, Dict, Optional

from src.core.llm_provider import LLMProvider


SYSTEM_PROMPT = """Bạn là chatbot hỗ trợ thương mại điện tử.
Chỉ trả lời ngắn gọn, đúng trọng tâm, bằng tiếng Việt.
Không gọi tool, không bịa dữ liệu tồn kho, giá bán, mã giảm giá, phí vận chuyển hoặc tổng tiền.
Nếu câu hỏi cần dữ liệu thực tế để xác minh hoặc tính toán, hãy nói rõ rằng cần agent/tool để kiểm tra.
Không được khẳng định đã tra cứu hay đã thực hiện hành động nào mà hệ thống không cung cấp."""


class ChatbotBaseline:
    """Baseline chatbot: exactly one LLM call and zero tool calls."""

    def __init__(self, llm: LLMProvider, system_prompt: str = SYSTEM_PROMPT):
        self.llm = llm
        self.system_prompt = system_prompt
        self.tool_calls = 0
        self.llm_calls = 0

    def run(self, user_input: str) -> str:
        self.llm_calls += 1
        response = self.llm.generate(user_input, system_prompt=self.system_prompt)
        if isinstance(response, dict):
            return str(response.get("content", ""))
        return str(response)

    def classify_output(self, user_input: str, answer: str) -> str:
        transactional_markers = ("buy", "total", "ship", "coupon", "stock", "iphone", "ipad", "macbook")
        lower_input = user_input.lower()
        lower_answer = answer.lower()
        if any(marker in lower_input for marker in transactional_markers):
            if any(marker in lower_answer for marker in ("verify", "tool", "cannot", "khong", "không")):
                return "safe_fallback"
            return "hallucinated"
        return "correct"
