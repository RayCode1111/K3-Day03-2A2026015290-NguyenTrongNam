from src.agent.agent import ReActAgent
from src.agent.agent_v2 import ReActAgentV2
from src.tools.tools import get_tool_registry
from tests.fakes import ScriptedLLM


def test_v1_repeats_until_step_budget_on_repeated_action_failure():
    llm = ScriptedLLM(
        [
            'Thought: Need stock.\nAction: check_stock({"item_name": "iPhone"})',
            'Thought: Still need stock.\nAction: check_stock({"item_name": "iPhone"})',
            'Thought: Still need stock.\nAction: check_stock({"item_name": "iPhone"})',
        ]
    )
    agent = ReActAgent(llm=llm, tools=get_tool_registry(), max_steps=3)

    answer = agent.run("Repeated action failure case")

    assert "step budget" in answer
    assert len([step for step in agent.trace if "action" in step]) == 3


def test_v2_stops_repeated_action_immediately():
    llm = ScriptedLLM(
        [
            'Thought: Need stock.\nAction: check_stock({"item_name": "iPhone"})',
            'Thought: Still need stock.\nAction: check_stock({"item_name": "iPhone"})',
        ]
    )
    agent = ReActAgentV2(llm=llm, tools=get_tool_registry(), max_steps=5)

    answer = agent.run("Repeated action failure case")

    assert "same tool call repeated" in answer
    assert agent.repeated_actions == 1
    assert len(agent.trace) == 2
