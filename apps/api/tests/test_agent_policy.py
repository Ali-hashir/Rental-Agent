from app.services.agent import SessionState, handle_turn


def test_budget_without_keyword_advances_flow() -> None:
    state = SessionState(session_id="t1")

    result = handle_turn(state, "Hello")
    assert result.stage == "gathering"

    result = handle_turn(state, "Need two bedrooms")
    assert result.stage == "gathering"

    result = handle_turn(state, "Prefer Clifton area")
    assert result.stage == "gathering"

    result = handle_turn(state, "120000")
    assert result.stage == "recommending"
    assert state.preferences.budget == 120000
    assert result.listing is not None

    result = handle_turn(state, "yes please")
    assert result.stage == "booking"

    result = handle_turn(state, "Ali")
    assert result.stage == "booking"

    result = handle_turn(state, "03001234567")
    assert result.stage == "completed"
    assert result.completed is True
    assert state.booking.contact == "03001234567"


def test_open_budget_phrase_allows_progress() -> None:
    state = SessionState(session_id="t2")

    handle_turn(state, "Hi")
    result = handle_turn(state, "Any number of bedrooms works for me")
    assert state.preferences.beds_open is True
    assert result.stage == "gathering"

    result = handle_turn(state, "Somewhere in Clifton please")
    assert result.stage == "gathering"

    result = handle_turn(state, "I dont have any budget i am open to whatever budget there is")
    assert result.stage == "recommending"
    assert state.preferences.budget is None
    assert state.preferences.budget_open is True
    assert result.listing is not None


def test_open_bed_and_bath_with_budget_limit() -> None:
    state = SessionState(session_id="t3")

    handle_turn(state, "Hello there")
    result = handle_turn(
        state,
        "I dont have any requirement as per bed or bath, i just need a place in clifton under 50000 rupee",
    )

    assert result.stage == "recommending"
    assert state.preferences.beds_open is True
    assert state.preferences.baths_open is True
    assert state.preferences.area == "Clifton"
    assert state.preferences.budget == 50000
    assert result.listing is not None
