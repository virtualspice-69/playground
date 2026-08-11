"""Simple in-memory per-user cooldown for commands that hit external APIs
(image generation) so a couple of enthusiastic users can't burn through the
free Pollinations tier or trip Telegram's flood limits for everyone."""

from __future__ import annotations

import time

import config

_last_call: dict[tuple[int, str], float] = {}


def check(user_id: int, command: str) -> float:
    """Returns 0 if the user may proceed, or the number of seconds they
    still need to wait otherwise."""
    key = (user_id, command)
    now = time.monotonic()
    last = _last_call.get(key)
    if last is not None:
        elapsed = now - last
        if elapsed < config.COMMAND_COOLDOWN_SECONDS:
            return round(config.COMMAND_COOLDOWN_SECONDS - elapsed, 1)
    _last_call[key] = now
    return 0
