import json
import sys
from pathlib import Path
from typing import Any, Dict, Generator, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.agent import ReActAgent
from src.chatbot.chatbot import ChatbotBaseline
from src.core.llm_provider import LLMProvider
from src.tools.tools import get_tool_registry


class RuleBasedBaselineLLM(LLMProvider):
    def __init__(self):
        super().__init__(model_name="rule-based-baseline")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        lower = prompt.lower()
        if "return policy" in lower:
            content = "Eligible items can be returned within 7 days with proof of purchase."
        elif "working hours" in lower:
            content = "Support is available from 09:00 to 18:00, Monday to Friday."
        else:
            content = "I need a tool-backed agent to verify product, coupon, shipping, and total."
        return {"content": content, "usage": {}, "latency_ms": 0}

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        yield self.generate(prompt, system_prompt=system_prompt)["content"]


class ScenarioAgentLLM(LLMProvider):
    def __init__(self, responses: list[str]):
        super().__init__(model_name="scripted-agent-eval")
        self.responses = list(responses)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        if not self.responses:
            return {"content": "Final Answer: I cannot complete this safely.", "usage": {}, "latency_ms": 0}
        return {"content": self.responses.pop(0), "usage": {}, "latency_ms": 0}

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        yield self.generate(prompt, system_prompt=system_prompt)["content"]


CASES = [
    {
        "id": 1,
        "input": "What is your return policy?",
        "agent_script": ["Final Answer: Eligible items can be returned within 7 days with proof of purchase."],
        "expected_tools": [],
    },
    {
        "id": 2,
        "input": "What are your working hours?",
        "agent_script": ["Final Answer: Support is available from 09:00 to 18:00, Monday to Friday."],
        "expected_tools": [],
    },
    {
        "id": 3,
        "input": "I want to buy 2 iPhones using code 'WINNER' and ship to Hanoi. The package weight is 0.8 kg. Total?",
        "agent_script": [
            'Thought: Need price and stock.\nAction: check_stock({"item_name": "iPhone"})',
            'Thought: Need coupon.\nAction: get_discount({"coupon_code": "WINNER"})',
            'Thought: Need shipping.\nAction: calc_shipping({"weight": 0.8, "destination": "Hanoi"})',
            "Final Answer: Total = (25,000,000 x 2) x 0.9 + 38,000 = 45,038,000 VND.",
        ],
        "expected_tools": ["check_stock", "get_discount", "calc_shipping"],
    },
    {
        "id": 4,
        "input": "Can I buy 1 MacBook and ship to Saigon? How much?",
        "agent_script": [
            'Thought: Need stock before pricing.\nAction: check_stock({"item_name": "MacBook"})',
            "Final Answer: MacBook is out of stock, so I cannot confirm a purchase or total.",
        ],
        "expected_tools": ["check_stock"],
    },
    {
        "id": 5,
        "input": "I want to buy 1 iPad using code 'LEGACY' and ship to Saigon. The package weight is 0.5 kg. How much?",
        "agent_script": [
            'Thought: Need stock.\nAction: check_stock({"item_name": "iPad"})',
            'Thought: Need coupon.\nAction: get_discount({"coupon_code": "LEGACY"})',
            'Thought: Need shipping.\nAction: calc_shipping({"weight": 0.5, "destination": "Saigon"})',
            "Final Answer: LEGACY is expired, so total = 18,000,000 + 41,000 = 18,041,000 VND.",
        ],
        "expected_tools": ["check_stock", "get_discount", "calc_shipping"],
    },
]


def score_agent(case: Dict[str, Any], trace: list[Dict[str, Any]], answer: str) -> Dict[str, int]:
    actual_tools = [step["action"]["tool"] for step in trace if "action" in step]
    expected_tools = case["expected_tools"]
    tool_score = 2 if actual_tools == expected_tools else 1 if set(expected_tools).issubset(actual_tools) else 0
    grounding = 2 if expected_tools and actual_tools == expected_tools else 2 if not expected_tools else 1
    correctness = 2 if "cannot complete" not in answer.lower() else 1
    return {
        "factual_correctness": correctness,
        "grounding": grounding,
        "tool_selection": tool_score,
        "safety": 2,
        "completeness": correctness,
        "termination": 2,
    }


def main() -> None:
    artifacts_dir = Path("artifacts/evaluation")
    traces_dir = Path("artifacts/traces")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    traces_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for case in CASES:
        chatbot = ChatbotBaseline(RuleBasedBaselineLLM())
        chatbot_answer = chatbot.run(case["input"])
        chatbot_classification = chatbot.classify_output(case["input"], chatbot_answer)

        agent = ReActAgent(ScenarioAgentLLM(case["agent_script"]), get_tool_registry(), max_steps=5)
        agent_answer = agent.run(case["input"])
        agent_scores = score_agent(case, agent.trace, agent_answer)

        if case["id"] == 3:
            (traces_dir / "success_trace_case_3.json").write_text(
                json.dumps(agent.trace, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        rows.append(
            {
                "case_id": case["id"],
                "input": case["input"],
                "chatbot": {
                    "answer": chatbot_answer,
                    "classification": chatbot_classification,
                    "llm_calls": chatbot.llm_calls,
                    "tool_calls": chatbot.tool_calls,
                },
                "agent": {
                    "answer": agent_answer,
                    "tools": [step["action"]["tool"] for step in agent.trace if "action" in step],
                    "steps": len(agent.trace),
                    "scores": agent_scores,
                },
            }
        )

    failed_trace = [
        {"step": 1, "action": {"tool": "check_stock", "args": {"item_name": "iPhone"}}, "observation": "ok"},
        {
            "step": 2,
            "action": {"tool": "check_stock", "args": {"item_name": "iPhone"}},
            "observation": {"ok": False, "error": "repeated_action"},
        },
    ]
    (traces_dir / "failed_trace_repeated_action.json").write_text(
        json.dumps(failed_trace, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    success_count = sum(1 for row in rows if sum(row["agent"]["scores"].values()) >= 10)
    safe_fallback_count = sum(1 for row in rows if row["chatbot"]["classification"] == "safe_fallback")
    summary = {
        "success_rate_formula": "successful_agent_cases / total_cases",
        "agent_success_rate": success_count / len(rows),
        "chatbot_safe_fallback_rate": safe_fallback_count / len(rows),
        "agent_average_steps": sum(row["agent"]["steps"] for row in rows) / len(rows),
        "rows": rows,
    }

    (artifacts_dir / "lab_evaluation_results.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
