import json
from typing import Any, Dict, List

from src.agent.agent import ReActAgent, _response_content, parse_action, parse_final_answer
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger


class ReActAgentV2(ReActAgent):
    """V2 adds a repeated-action guard based on the failed trace."""

    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]] | Dict[str, Dict[str, Any]], max_steps: int = 5):
        super().__init__(llm=llm, tools=tools, max_steps=max_steps)
        self.repeated_actions = 0

    def run(self, user_input: str) -> str:
        logger.log_event("AGENT_V2_START", {"input": user_input, "model": self.llm.model_name})

        transcript = f"Question: {user_input}"
        self.trace = []
        previous_action = None

        for step in range(1, self.max_steps + 1):
            response = _response_content(self.llm.generate(transcript, system_prompt=self.get_system_prompt()))
            final_answer = parse_final_answer(response)
            if final_answer:
                self.trace.append({"step": step, "llm_output": response, "final_answer": final_answer})
                return final_answer

            try:
                action = parse_action(response)
            except ValueError as exc:
                observation = {"ok": False, "error": "parse_error", "message": str(exc)}
                transcript += f"\n{response}\nObservation: {json.dumps(observation, ensure_ascii=False)}"
                self.trace.append({"step": step, "llm_output": response, "observation": observation})
                continue

            if not action:
                observation = {"ok": False, "error": "missing_action", "message": "Use Action or Final Answer format."}
                transcript += f"\n{response}\nObservation: {json.dumps(observation, ensure_ascii=False)}"
                self.trace.append({"step": step, "llm_output": response, "observation": observation})
                continue

            tool_name, args = action
            action_key = (tool_name, json.dumps(args, sort_keys=True))
            if action_key == previous_action:
                self.repeated_actions += 1
                fallback = "I stopped because the same tool call repeated without new evidence."
                self.trace.append(
                    {
                        "step": step,
                        "llm_output": response,
                        "action": {"tool": tool_name, "args": args},
                        "observation": {"ok": False, "error": "repeated_action", "message": fallback},
                    }
                )
                return fallback

            previous_action = action_key
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

        return "I cannot complete this safely within the step budget."
