from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CompiledTitleMatcher:
    regex: re.Pattern[str] | None
    lowered_pattern: str


def compile_title_matcher(pattern: str, use_regex: bool) -> CompiledTitleMatcher | None:
    value = pattern.strip()
    if not value:
        return None
    if use_regex:
        try:
            return CompiledTitleMatcher(regex=re.compile(value, re.IGNORECASE), lowered_pattern="")
        except re.error:
            return None
    return CompiledTitleMatcher(regex=None, lowered_pattern=value.lower())


def title_matches(matcher: CompiledTitleMatcher, title: str) -> bool:
    if matcher.regex is not None:
        return bool(matcher.regex.search(title))
    return matcher.lowered_pattern in title.lower()
