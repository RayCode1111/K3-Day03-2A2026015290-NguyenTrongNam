import os
import time
from typing import Any, Dict, Generator, Optional

from dotenv import load_dotenv, find_dotenv
from src.core.llm_provider import LLMProvider

try:
    from google import genai
    from google.genai import types
except ImportError as exc:  # pragma: no cover - dependency issue is environment-specific.
    genai = None
    types = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


class GeminiProvider(LLMProvider):
    def __init__(self, model_name: str = "gemini-3.6-flash", api_key: Optional[str] = None):
        load_dotenv(find_dotenv(usecwd=True), override=False)
        resolved_api_key = (api_key or os.getenv("GEMINI_API_KEY") or "").strip() or None
        super().__init__(model_name, resolved_api_key)

        if genai is None:
            raise ImportError(
                "google-genai is not installed. Install it with `pip install google-genai`."
            ) from _IMPORT_ERROR

        self.client = genai.Client(api_key=self.api_key)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()

        config = None
        if system_prompt:
            config = types.GenerateContentConfig(system_instruction=system_prompt)

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )

        latency_ms = int((time.time() - start_time) * 1000)
        usage = response.usage_metadata

        return {
            "content": response.text,
            "usage": {
                "prompt_tokens": getattr(usage, "prompt_token_count", 0),
                "completion_tokens": getattr(usage, "candidates_token_count", 0),
                "total_tokens": getattr(usage, "total_token_count", 0),
            },
            "latency_ms": latency_ms,
            "provider": "google",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        config = None
        if system_prompt:
            config = types.GenerateContentConfig(system_instruction=system_prompt)

        response_stream = self.client.models.generate_content_stream(
            model=self.model_name,
            contents=prompt,
            config=config,
        )

        for chunk in response_stream:
            if getattr(chunk, "text", None):
                yield chunk.text
