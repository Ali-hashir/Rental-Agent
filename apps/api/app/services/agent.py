"""Conversation policy for the rental voice agent."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Literal, Optional

from ..data.listings import AREA_ALIASES, LISTINGS, Listing

Stage = Literal["greeting", "gathering", "recommending", "booking", "completed"]

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
}

POSITIVE_PATTERNS = re.compile(r"\b(yes|yeah|book|schedule|sounds good|interested|sure|ok|okay)\b", re.I)
NEGATIVE_PATTERNS = re.compile(r"\b(no|another|different|other|not really)\b", re.I)
BEDS_OPEN_HINTS = (
    "no requirement",
    "no specific",
    "no preference",
    "dont care",
    "don't care",
    "any bed",
    "any bedroom",
    "whatever bed",
    "no beds needed",
    "no bedroom requirement",
    "bed doesn't matter",
)
BATHS_OPEN_HINTS = (
    "no requirement",
    "no specific",
    "no preference",
    "dont care",
    "don't care",
    "any bath",
    "any bathroom",
    "whatever bath",
    "bath doesn't matter",
)
BUDGET_OPEN_HINTS = (
    "no budget",
    "dont have any budget",
    "don't have any budget",
    "budget doesn't matter",
    "open to whatever budget",
    "any budget",
    "whatever budget",
    "budget is flexible",
    "price doesn't matter",
    "no price limit",
    "no price requirement",
    "open budget",
    "i'm open on budget",
)
NAME_PATTERNS = [
    re.compile(r"my name is (?P<name>[a-zA-Z\s']+)", re.I),
    re.compile(r"this is (?P<name>[a-zA-Z\s']+)", re.I),
    re.compile(r"i am (?P<name>[a-zA-Z\s']+)", re.I),
]
EMAIL_PATTERN = re.compile(r"[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"\+?\d[\d\s-]{6,}")
BEDS_PATTERN = re.compile(r"(\d+)\s*(?:bed|bedroom)", re.I)
BATH_PATTERN = re.compile(r"(\d+)\s*(?:bath|bathroom)", re.I)
GENERIC_NUMBER_PATTERN = re.compile(r"(\d+)(?:\s*(k|thousand))?", re.I)
BED_KEYWORDS = ("bed", "beds", "bedroom", "bedrooms")
BATH_KEYWORDS = ("bath", "baths", "bathroom", "bathrooms")
BUDGET_KEYWORDS = (
    "budget",
    "rent",
    "under",
    "rupee",
    "rupees",
    "rs",
    "pkr",
    "price",
    "cost",
    "around",
    "approx",
    "approximately",
    "about",
    "within",
)
OPEN_GENERAL_HINTS = (
    "any",
    "whatever",
    "either",
    "no preference",
    "no requirement",
    "dont care",
    "don't care",
    "no specific",
    "not fussed",
    "no particular",
    "open to any",
    "open on",
)


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _has_open_preference(text: str, keywords: tuple[str, ...], hints: tuple[str, ...]) -> bool:
    if not any(keyword in text for keyword in keywords):
        return False
    if _contains_any(text, hints):
        return True
    return any(open_hint in text for open_hint in OPEN_GENERAL_HINTS)


@dataclass
class Preferences:
    beds: Optional[int] = None
    baths: Optional[int] = None
    area: Optional[str] = None
    budget: Optional[int] = None
    move_in: Optional[str] = None
    beds_open: bool = False
    baths_open: bool = False
    budget_open: bool = False


@dataclass
class BookingInfo:
    name: Optional[str] = None
    contact: Optional[str] = None
    contact_method: Optional[str] = None
    preferred_slot: Optional[str] = None


@dataclass
class SessionState:
    session_id: str
    stage: Stage = "greeting"
    preferences: Preferences = field(default_factory=Preferences)
    booking: BookingInfo = field(default_factory=BookingInfo)
    history: List[dict[str, str]] = field(default_factory=list)
    proposed_listing_id: Optional[str] = None
    dismissed_listing_ids: set[str] = field(default_factory=set)
    last_prompt: Optional[str] = None


@dataclass
class AgentTurnResult:
    reply_text: str
    stage: Stage
    listing: Optional[Listing]
    collected_preferences: Preferences
    completed: bool = False


def handle_turn(state: SessionState, user_text: str) -> AgentTurnResult:
    """Update the session based on the visitor utterance and return the agent reply."""

    cleaned_text = user_text.strip()
    state.history.append({"role": "user", "content": cleaned_text})
    _extract_preferences(state.preferences, cleaned_text)
    _maybe_fill_budget_from_context(state.preferences, cleaned_text, state.last_prompt)

    if state.stage == "greeting":
        state.stage = "gathering"
        reply = (
            "Hi there! I'm the leasing assistant. I'll help you find an apartment. "
            "Could you tell me how many bedrooms you need?"
        )
        state.last_prompt = "beds"
        return _finalize_turn(state, reply)

    if state.stage == "gathering":
        missing = _missing_preferences(state.preferences)
        if missing:
            prompt = missing[0]
            state.last_prompt = prompt
            reply = _build_question_for_slot(prompt)
            return _finalize_turn(state, reply)

        listing = _select_listing(state)
        if listing:
            state.proposed_listing_id = listing.id
            state.stage = "recommending"
            reply = _describe_listing(listing)
            return _finalize_turn(state, reply, listing)

        reply = (
            "I don't have an exact match yet, but we currently have options in Clifton and Gulshan. "
            "Would you like to hear about those?"
        )
        state.last_prompt = "confirm_alt"
        return _finalize_turn(state, reply)

    if state.stage == "recommending":
        if POSITIVE_PATTERNS.search(cleaned_text):
            state.stage = "booking"
            state.last_prompt = "name"
            reply = "Great choice! Could I have your name to pencil you in for a viewing?"
            return _finalize_turn(state, reply, _current_listing(state))

        if NEGATIVE_PATTERNS.search(cleaned_text):
            _dismiss_current_listing(state)
            new_listing = _select_listing(state)
            if new_listing:
                state.proposed_listing_id = new_listing.id
                reply = _describe_listing(new_listing, offer_alternative=True)
                return _finalize_turn(state, reply, new_listing)
            reply = (
                "No problem. Those are the only units in our demo catalog right now, "
                "but I can note your preferences for when new listings arrive."
            )
            state.stage = "completed"
            return _finalize_turn(state, reply, completed=True)

        reply = (
            "Take your time. If you'd like to book a viewing or hear about another listing, just let me know."
        )
        return _finalize_turn(state, reply, _current_listing(state))

    if state.stage == "booking":
        if not state.booking.name:
            name = _extract_name(cleaned_text)
            if name:
                state.booking.name = name
                state.last_prompt = "contact"
                reply = f"Thanks {name}! What's the best phone number or email to reach you for confirmation?"
                return _finalize_turn(state, reply, _current_listing(state))
            reply = "Could you please share your name so I can hold the slot?"
            return _finalize_turn(state, reply, _current_listing(state))

        if not state.booking.contact:
            contact, method = _extract_contact(cleaned_text)
            if contact:
                state.booking.contact = contact
                state.booking.contact_method = method
                state.stage = "completed"
                state.last_prompt = None
                listing = _current_listing(state)
                reply = (
                    f"Perfect! I'll reserve the {listing.title if listing else 'listing'} and reach out at {contact}. "
                    "A teammate will confirm the viewing shortly. Is there anything else I can help with?"
                )
                return _finalize_turn(state, reply, listing, completed=True)
            reply = "No worries—could you share a phone number or email so we can confirm the viewing?"
            return _finalize_turn(state, reply, _current_listing(state))

        reply = "I'm putting everything together—let me know if you'd like to adjust the viewing details."
        return _finalize_turn(state, reply, _current_listing(state))

    # Completed stage
    if "thank" in cleaned_text.lower():
        reply = "You're welcome! Happy to help."
    else:
        reply = "If you need anything else regarding our listings, just let me know."
    return _finalize_turn(state, reply, _current_listing(state), completed=True)


def _finalize_turn(
    state: SessionState,
    reply: str,
    listing: Optional[Listing] = None,
    completed: bool = False,
) -> AgentTurnResult:
    state.history.append({"role": "assistant", "content": reply})
    return AgentTurnResult(
        reply_text=reply,
        stage=state.stage,
        listing=listing,
        collected_preferences=state.preferences,
        completed=completed,
    )


def _missing_preferences(prefs: Preferences) -> List[str]:
    missing: List[str] = []
    if prefs.beds is None and not prefs.beds_open:
        missing.append("beds")
    if prefs.area is None:
        missing.append("area")
    if prefs.budget is None and not prefs.budget_open:
        missing.append("budget")
    return missing


def _build_question_for_slot(slot: str) -> str:
    if slot == "beds":
        return "How many bedrooms are you looking for?"
    if slot == "area":
        return "Which neighborhood suits you best? We currently have Clifton and Gulshan available."
    if slot == "budget":
        return "What's your ideal monthly budget in PKR?"
    if slot == "baths":
        return "Do you have a preference for the number of bathrooms?"
    return "Could you share a bit more about what you're looking for?"


def _extract_preferences(prefs: Preferences, text: str) -> None:
    lower_text = text.lower()

    beds_match = BEDS_PATTERN.search(lower_text)
    if beds_match:
        prefs.beds = int(beds_match.group(1))
        prefs.beds_open = False
    else:
        for word, value in NUMBER_WORDS.items():
            if f"{word} bed" in lower_text:
                prefs.beds = value
                prefs.beds_open = False
                break

    if prefs.beds is None and _has_open_preference(lower_text, BED_KEYWORDS, BEDS_OPEN_HINTS):
        prefs.beds_open = True

    baths_match = BATH_PATTERN.search(lower_text)
    if baths_match:
        prefs.baths = int(baths_match.group(1))
        prefs.baths_open = False
    elif _has_open_preference(lower_text, BATH_KEYWORDS, BATHS_OPEN_HINTS):
        prefs.baths_open = True

    for alias, area in AREA_ALIASES.items():
        if alias in lower_text:
            prefs.area = area
            break

    budget = _extract_budget(lower_text)
    if budget:
        prefs.budget = budget
        prefs.budget_open = False
    elif _contains_any(lower_text, BUDGET_OPEN_HINTS):
        prefs.budget_open = True

    if "move" in lower_text or "from" in lower_text:
        prefs.move_in = text.strip()


def _extract_budget(text: str) -> Optional[int]:
    return _extract_budget_with_mode(text, require_keyword=True)


def _maybe_fill_budget_from_context(prefs: Preferences, text: str, last_prompt: Optional[str]) -> None:
    if prefs.budget is not None:
        return
    if prefs.budget_open:
        return
    if last_prompt != "budget":
        return
    value = _extract_budget_with_mode(text.lower(), require_keyword=False)
    if value:
        prefs.budget = value


def _extract_budget_with_mode(text: str, *, require_keyword: bool) -> Optional[int]:
    if require_keyword and not any(keyword in text for keyword in BUDGET_KEYWORDS):
        return None

    best = None
    for match in GENERIC_NUMBER_PATTERN.finditer(text):
        value = int(match.group(1))
        if match.group(2):
            value *= 1000
        elif value < 500:  # assume shorthand like 120 stands for 120,000
            value *= 1000
        best = value
    return best


def _select_listing(state: SessionState) -> Optional[Listing]:
    prefs = state.preferences
    candidates = [listing for listing in LISTINGS if listing.id not in state.dismissed_listing_ids]

    if prefs.area:
        candidates = [listing for listing in candidates if listing.area.lower() == prefs.area.lower()]

    if prefs.beds is not None:
        candidates = [listing for listing in candidates if listing.beds >= prefs.beds]

    if prefs.budget is not None:
        within = [listing for listing in candidates if listing.rent <= prefs.budget]
        if within:
            candidates = within

    if not candidates:
        return None

    candidates.sort(key=lambda listing: listing.rent)
    return candidates[0]


def _describe_listing(listing: Listing, offer_alternative: bool = False) -> str:
    base = (
        f"I recommend the {listing.title} in {listing.area}. It's PKR {listing.rent:,} per month "
        f"at {listing.address}. {listing.notes}"
    )
    amenities = ""
    if listing.amenities:
        amenities = " Amenities include " + ", ".join(listing.amenities) + "."
    slots = ""
    if listing.viewing_slots:
        slots = " Available viewing slots include " + ", ".join(listing.viewing_slots[:2]) + "."

    closing = " Would you like me to book a viewing?" if not offer_alternative else " Does this sound better?"
    return base + amenities + slots + closing


def _dismiss_current_listing(state: SessionState) -> None:
    if state.proposed_listing_id:
        state.dismissed_listing_ids.add(state.proposed_listing_id)
        state.proposed_listing_id = None


def _current_listing(state: SessionState) -> Optional[Listing]:
    if not state.proposed_listing_id:
        return None
    for listing in LISTINGS:
        if listing.id == state.proposed_listing_id:
            return listing
    return None


def _extract_name(text: str) -> Optional[str]:
    for pattern in NAME_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group("name").strip().title()

    tokens = text.split()
    if len(tokens) <= 3:
        candidate = text.strip().title()
        if candidate and candidate.lower() not in {"yes", "yeah", "no", "hi", "hello"}:
            return candidate
    return None


def _extract_contact(text: str) -> tuple[Optional[str], Optional[str]]:
    email = EMAIL_PATTERN.search(text)
    if email:
        return email.group(0), "email"

    phone = PHONE_PATTERN.search(text)
    if phone:
        cleaned = re.sub(r"\s+", " ", phone.group(0)).strip()
        return cleaned, "phone"
    return None, None
