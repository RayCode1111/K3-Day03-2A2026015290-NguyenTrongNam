from src.agent.agent import ReActAgent, parse_action, parse_final_answer
from src.tools.tools import get_tool_registry
from tests.fakes import ScriptedLLM


def test_parse_action_and_final_answer():
    assert parse_action('Thought: x\nAction: check_stock({"item_name": "iPhone"})') == (
        "check_stock",
        {"item_name": "iPhone"},
    )
    assert parse_final_answer("Final Answer: Done") == "Done"


def test_agent_runs_three_tool_sequence_and_passes_observations_forward():
    llm = ScriptedLLM(
        [
            'Thought: Need stock.\nAction: check_stock({"item_name": "iPhone"})',
            'Thought: Need coupon.\nAction: get_discount({"coupon_code": "WINNER"})',
            'Thought: Need shipping.\nAction: calc_shipping({"weight": 0.8, "destination": "Hanoi"})',
            "Final Answer: Total = 45,038,000 VND.",
        ]
    )
    agent = ReActAgent(llm=llm, tools=get_tool_registry(), max_steps=5)

    answer = agent.run("2 iPhones, WINNER coupon, ship to Hanoi, weight 0.8kg. Total?")

    assert "45,038,000" in answer
    assert [step["action"]["tool"] for step in agent.trace if "action" in step] == [
        "check_stock",
        "get_discount",
        "calc_shipping",
    ]
    assert "Observation:" in llm.prompts[1]
    assert "check_stock" in llm.prompts[1]
    assert len(agent.trace) == 4
