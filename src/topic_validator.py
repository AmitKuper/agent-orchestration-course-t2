"""Validates debate topics and extracts opposing positions."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.exceptions import InvalidTopicError

if TYPE_CHECKING:
    from src.backends import Backend


def validate_topic(
    topic: str, model: str, backend: Backend | None = None
) -> tuple[str, str]:
    """Ask a model whether a topic can be split into two opposing debatable sides.

    Args:
        topic: The raw debate topic string to evaluate.
        model: Model ID to use for the validation call.
        backend: Invocation backend. If None, falls back to the Anthropic SDK.

    Returns:
        Tuple of (position_a, position_b) — the two opposing sides.

    Raises:
        InvalidTopicError: If the model determines the topic is not clearly debatable.
    """
    prompt = (
        f"Does '{topic}' split into two opposing debatable positions? "
        f'JSON only: {{"valid":true,"position_a":"...","position_b":"..."}} '
        f'or {{"valid":false,"reason":"..."}}'
    )

    if backend is not None:
        from src.cost import CostTracker
        raw = backend.invoke("validator", model, prompt, CostTracker("validator"), 256)
    else:
        import anthropic
        msg = anthropic.Anthropic().messages.create(
            model=model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text

    # Strip markdown code fences if the model wrapped the JSON
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    result = json.loads(text)
    if not result.get("valid"):
        raise InvalidTopicError(result.get("reason", "Topic is not debatable."))
    return result["position_a"], result["position_b"]
