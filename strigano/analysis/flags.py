"""Flag pattern matching, driven by the prefixes in config."""

from __future__ import annotations

import re

from .. import config


def build_flag_regex(prefixes: list[str] | None = None) -> re.Pattern[str]:
    """Compile a regex matching ``prefix{...}`` for every configured prefix."""
    prefixes = prefixes or config.FLAG_PREFIXES
    alt = "|".join(re.escape(p) for p in sorted(set(prefixes), key=len, reverse=True))
    return re.compile(rf"(?:{alt})\{{[^}}\n]{{1,256}}\}}", re.IGNORECASE)


FLAG_REGEX = build_flag_regex()


def find_flags(text: str) -> list[str]:
    """Return de-duplicated flag-looking substrings found in ``text``."""
    if not text:
        return []
    seen: dict[str, None] = {}
    for match in FLAG_REGEX.findall(text):
        seen.setdefault(match.strip(), None)
    return list(seen)
