from src.chatbot.chatbot import ChatbotBaseline
from tests.fakes import ScriptedLLM


def test_chatbot_static_policy_is_one_llm_call_and_no_tools():
    llm = ScriptedLLM(["You can return eligible items within 7 days."])
    bot = ChatbotBaseline(llm)

    answer = bot.run("What is your return policy?")

    assert "7 days" in answer
    assert bot.llm_calls == 1
    assert bot.tool_calls == 0
    assert bot.classify_output("What is your return policy?", answer) == "correct"


def test_chatbot_multistep_order_uses_safe_fallback_not_fake_total():
    llm = ScriptedLLM(["I need a tool-backed agent to verify price, coupon, shipping, and total."])
    bot = ChatbotBaseline(llm)

    answer = bot.run("I want to buy 2 iPhones using WINNER and ship to Hanoi. Total?")

    assert bot.llm_calls == 1
    assert bot.tool_calls == 0
    assert bot.classify_output("buy 2 iPhones using WINNER and ship to Hanoi", answer) == "safe_fallback"
