import pytest

from app.services import agent, llm


@pytest.mark.asyncio
async def test_generate_reply_without_api_key_uses_policy_template(monkeypatch) -> None:
    monkeypatch.setattr(llm.settings, "gemini_api_key", "", raising=False)

    state = agent.SessionState(session_id="test")
    turn = agent.AgentTurnResult(
        reply_text="Policy fallback reply.",
        stage="gathering",
        listing=None,
        collected_preferences=state.preferences,
    )

    result = await llm.generate_reply("hello", agent_result=turn, state=state)

    assert result == "Policy fallback reply."
