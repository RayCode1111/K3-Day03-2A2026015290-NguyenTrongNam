import json
import re
from typing import Any, Dict, List, Optional, Tuple
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger


def _response_content(response: Any) -> str:
    if isinstance(response, dict):
        return str(response.get("content", ""))
    return str(response)


def parse_final_answer(text: str) -> Optional[str]:
    match = re.search(r"Final Answer\s*:\s*(.+)", text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return match.group(1).strip()


def _strip_code_fence(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
        raw = re.sub(r"```$", "", raw).strip()
    return raw


def parse_action(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    match = re.search(r"Action\s*:\s*([A-Za-z_][\w]*)\s*\((\{.*?\})\)", text, flags=re.DOTALL)
    if not match:
        return None

    tool_name = match.group(1)
    raw_args = _strip_code_fence(match.group(2))
    try:
        args = json.loads(raw_args)
    except json.JSONDecodeError:
        try:
            import ast

            args = ast.literal_eval(raw_args)
        except (SyntaxError, ValueError) as exc:
            raise ValueError(f"Could not parse Action arguments: {raw_args}") from exc

    if not isinstance(args, dict):
        raise ValueError("Action arguments must be a JSON object.")
    return tool_name, args


class ReActAgent:
    """A ReAct-style agent that follows the Thought-Action-Observation loop."""
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]] | Dict[str, Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = list(tools.values()) if isinstance(tools, dict) else tools
        self.registry = {tool["name"]: tool for tool in self.tools}
        self.max_steps = max_steps
        self.history = []
        self.trace = []

    def get_system_prompt(self) -> str:
        """
        System prompt that instructs the agent to follow ReAct.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        return f"""
        You are an e-commerce ReAct agent. Use tools for product, coupon, shipping,
        and total-price questions. Do not invent tools or observations.

        Available tools:
        {tool_descriptions}

        Use the following format:
        Thought: short reasoning.
        Action: tool_name({{"argument": "value"}})

        The application will add Observation. Only write Observation if it is already
        present in the conversation. When enough evidence is available, respond:
        Final Answer: your final response.
        """

    def run(self, user_input: str) -> str:
        """
        Run the ReAct loop: LLM -> Action -> tool Observation -> LLM.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})

        transcript = f"Question: {user_input}"
        self.trace = []

        for step in range(1, self.max_steps + 1):
            response = _response_content(self.llm.generate(transcript, system_prompt=self.get_system_prompt()))
            final_answer = parse_final_answer(response)
            if final_answer:
                self.trace.append({"step": step, "llm_output": response, "final_answer": final_answer})
                logger.log_event("AGENT_END", {"steps": step, "status": "final"})
                return final_answer

            try:
                action = parse_action(response)
            except ValueError as exc:
                observation = {"ok": False, "error": "parse_error", "message": str(exc)}
                transcript += f"\n{response}\nObservation: {json.dumps(observation, ensure_ascii=False)}"
                self.trace.append({"step": step, "llm_output": response, "observation": observation})
                continue

            if not action:
                observation = {
                    "ok": False,
                    "error": "missing_action",
                    "message": "Use Action or Final Answer format.",
                }
                transcript += f"\n{response}\nObservation: {json.dumps(observation, ensure_ascii=False)}"
                self.trace.append({"step": step, "llm_output": response, "observation": observation})
                continue

            tool_name, args = action
            observation = self._execute_tool(tool_name, args)
            transcript += f"\n{response}\nObservation: {json.dumps(observation, ensure_ascii=False)}"
            self.trace.append(
                {
                    "step": step,
                    "llm_output": response,
                    "action": {"tool": tool_name, "args": args},
                    "observation": observation,
                }
            )

        logger.log_event("AGENT_END", {"steps": self.max_steps, "status": "max_steps"})
        return "I cannot complete this safely within the step budget."

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        tool = self.registry.get(tool_name)
        if tool is None:
            return {
                "ok": False,
                "error": "unknown_tool",
                "message": f"Tool '{tool_name}' is not available.",
                "available_tools": sorted(self.registry),
            }
        try:
            return tool["function"](**args)
        except TypeError as exc:
            return {"ok": False, "error": "invalid_arguments", "message": str(exc)}
        except Exception as exc:  # pragma: no cover - defensive wrapper for tool bugs.
            return {"ok": False, "error": "tool_exception", "message": str(exc)}
