"""LLM helper built on Gemini Flash Lite."""
from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from typing import Dict, List, Optional

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from ..core.config import settings
from ..data.listings import LISTINGS, Listing
from .agent import AgentTurnResult, Preferences, SessionState

FALLBACK_SYSTEM_PROMPT = (
    "You are a polite apartment receptionist. Be brief. If the visitor asks about rent or beds, "
    "answer with short plain sentences. If you do not know a number, say you don’t know. Do not "
    "ask for payment. One or two sentences only."
)

AGENT_SYSTEM_PROMPT = (
    "You speak as a friendly human leasing assistant over a phone call. Follow the policy guidance "
    "given, keep the response to one or two short sentences, and do not invent any new facts beyond "
    "the supplied listing details."
)

logger = logging.getLogger(__name__)


class LLMUnavailableError(RuntimeError):
    """Raised when no configured Gemini models are available."""


def _has_api_key() -> bool:
    return bool(settings.gemini_api_key.strip())


@lru_cache
def _configured_api() -> bool:
    """Configure the Google Generative AI client once."""

    if not _has_api_key():
        raise RuntimeError("GEMINI_API_KEY is missing")

    genai.configure(api_key=settings.gemini_api_key)
    return True


_model_cache: Dict[str, genai.GenerativeModel] = {}
_LAST_REPLY_SOURCE: str = "unknown"


def _set_last_reply_source(source: str) -> None:
    """Record where the last reply came from for observability."""

    global _LAST_REPLY_SOURCE
    _LAST_REPLY_SOURCE = source


def get_reply_source() -> str:
    """Expose the last reply source to the API layer."""

    return _LAST_REPLY_SOURCE


@lru_cache
def _compose_catalog() -> str:
    lines = ["Available units:"]
    for listing in LISTINGS:
        notes = f" ({listing.notes})" if listing.notes else ""
        lines.append(
            f"- {listing.title} — {listing.beds} beds, PKR {listing.rent:,} in {listing.area}{notes}"
        )
    return "\n".join(lines)


def _get_model(name: str) -> genai.GenerativeModel:
    """Return a cached Gemini model instance."""

    _configured_api()
    model_name = name.strip()
    if not model_name:
        raise RuntimeError("Gemini model name was empty")

    if model_name not in _model_cache:
        _model_cache[model_name] = genai.GenerativeModel(model_name)
    return _model_cache[model_name]


def _summarize_preferences(prefs: Preferences) -> str:
    details: list[str] = []
    if getattr(prefs, "beds_open", False) and prefs.beds is None:
        details.append("beds=any")
    elif prefs.beds is not None:
        details.append(f"beds={prefs.beds}")

    baths_value = getattr(prefs, "baths", None)
    baths_open = getattr(prefs, "baths_open", False)
    if baths_open and baths_value is None:
        details.append("baths=any")
    elif baths_value is not None:
        details.append(f"baths={baths_value}")

    if prefs.area:
        details.append(f"area={prefs.area}")
    if getattr(prefs, "budget_open", False) and prefs.budget is None:
        details.append("budget=open")
    elif prefs.budget is not None:
        details.append(f"budget≈PKR {prefs.budget:,}")
    if prefs.move_in:
        details.append("move_in mentioned")
    return ", ".join(details) if details else "none captured yet"


def _describe_listing_for_prompt(listing: Listing | None) -> str:
    if listing is None:
        return "no listing yet"

    parts = [
        f"{listing.title} in {listing.area}",
        f"PKR {listing.rent:,} per month",
        f"Address: {listing.address}",
    ]
    if listing.notes:
        parts.append(f"Notes: {listing.notes}")
    if listing.amenities:
        parts.append("Amenities: " + ", ".join(listing.amenities))
    if listing.viewing_slots:
        parts.append("Viewing slots: " + ", ".join(listing.viewing_slots[:3]))
    return "; ".join(parts)


def _format_history(history: List[dict[str, str]], limit: int | None = None) -> str:
    if not history:
        return "No prior dialogue."
    trimmed = history[-limit:] if limit else history
    lines = [f"{entry['role'].title()}: {entry['content']}" for entry in trimmed]
    return "\n".join(lines)


def _build_agent_prompt(user_text: str, turn: AgentTurnResult, state: SessionState) -> str:
    prior_messages = state.history[:-1] if state.history and state.history[-1].get("role") == "assistant" else state.history
    history_block = _format_history(prior_messages)
    preferences = _summarize_preferences(turn.collected_preferences)
    listing_summary = _describe_listing_for_prompt(turn.listing)
    completion_hint = "The booking workflow is already complete." if turn.completed else ""

    lines = [
        AGENT_SYSTEM_PROMPT,
        "",
        "Conversation so far:",
        history_block,
        "",
        f"Latest visitor utterance: {user_text.strip() or '...'}",
        "",
        f"Policy guidance: {turn.reply_text}",
        f"Current stage: {turn.stage}",
        f"Collected preferences: {preferences}",
        f"Highlighted listing: {listing_summary}",
    ]
    if completion_hint:
        lines.append(completion_hint)
    lines.extend(
        [
            "",
            "Rewrite the policy guidance into a natural spoken reply. Use friendly, confident tone.",
            "Keep it within two short sentences and do not invent new facts.",
            "Assistant:",
        ]
    )
    return "\n".join(lines)


async def generate_reply(
    user_text: str,
    *,
    agent_result: Optional[AgentTurnResult] = None,
    state: Optional[SessionState] = None,
) -> str:
    """Return a brief, catalog-grounded reply for the visitor question."""

    loop = asyncio.get_running_loop()
    if agent_result is not None and state is not None:
        prompt = _build_agent_prompt(user_text, agent_result, state)
    else:
        prompt = (
            f"{FALLBACK_SYSTEM_PROMPT}\n\n{_compose_catalog()}\n\n"
            f"Visitor: {user_text.strip()}\nReceptionist:"
        )

    if not _has_api_key():
        if agent_result is not None:
            logger.warning("Gemini API key missing; falling back to policy template reply.")
            _set_last_reply_source("policy-template")
            return agent_result.reply_text
        raise LLMUnavailableError("GEMINI_API_KEY is missing")
    candidates: list[str] = []
    seen: set[str] = set()
    for candidate in (settings.gemini_model, *settings.gemini_model_fallbacks):
        if candidate and candidate not in seen:
            candidates.append(candidate)
            seen.add(candidate)

    last_error: Exception | None = None

    for model_name in candidates:
        def _run_inference(current_model: str = model_name) -> str:
            response = _get_model(current_model).generate_content(prompt)
            text = getattr(response, "text", "") or ""
            return text.strip()

        try:
            result = await loop.run_in_executor(None, _run_inference)
            if result:
                _set_last_reply_source(model_name)
                return result
            if agent_result is not None:
                _set_last_reply_source("policy-template")
                return agent_result.reply_text
            _set_last_reply_source("unknown")
            return result
        except google_exceptions.NotFound as exc:
            logger.warning("Gemini model %s not available: %s", model_name, exc)
            _model_cache.pop(model_name, None)
            last_error = exc
            continue
        except Exception as exc:  # noqa: BLE001
            logger.exception("Gemini generate_content failed for %s", model_name)
            last_error = exc
            continue

    if agent_result is not None:
        logger.warning("All Gemini models unavailable; using policy template reply.")
        _set_last_reply_source("policy-template")
        return agent_result.reply_text

    raise LLMUnavailableError("No Gemini models responded") from last_error
