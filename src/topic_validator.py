"""Validates debate topics and extracts opposing positions via a Claude API call."""

from __future__ import annotations

import json

import anthropic

from src.exceptions import InvalidTopicError


def validate_topic(topic: str, model: str) -> tuple[str, str]:
    """Ask Claude whether a topic can be split into two opposing debatable sides.

    Makes a single Claude API call to evaluate the topic and extract positions.

    Args:
        topic: The raw debate topic string to evaluate.
        model: Claude model ID to use for the validation call.

    Returns:
        Tuple of (position_a, position_b) — the two opposing sides.

    Raises:
        InvalidTopicError: If Claude determines the topic is not clearly debatable.
    """
    msg = anthropic.Anthropic().messages.create(
        model=model,
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Does '{topic}' split into two opposing debatable positions? "
                    f'JSON only: {{"valid":true,"position_a":"...","position_b":"..."}} '
                    f'or {{"valid":false,"reason":"..."}}'
                ),
            }
        ],
    )
    result = json.loads(msg.content[0].text)
    if not result.get("valid"):
        raise InvalidTopicError(result.get("reason", "Topic is not debatable."))
    return result["position_a"], result["position_b"]
