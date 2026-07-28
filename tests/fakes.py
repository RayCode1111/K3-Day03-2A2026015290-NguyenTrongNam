from typing import Any, Dict, Generator, Optional

from src.core.llm_provider import LLMProvider


class ScriptedLLM(LLMProvider):
    def __init__(self, responses: list[str], model_name: str = "scripted-test-model"):
        super().__init__(model_name=model_name)
        self.responses = list(responses)
        self.prompts: list[str] = []

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        self.prompts.append(prompt)
        if not self.responses:
            return {"content": "Final Answer: I cannot continue.", "usage": {}, "latency_ms": 0}
        return {"content": self.responses.pop(0), "usage": {}, "latency_ms": 0}

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        yield self.generate(prompt, system_prompt=system_prompt)["content"]
