"""
Incoming rich message model.

RichMessage is intentionally data-only.  It exposes the Telegram-backed raw
representation without implementing transport, parsing, or conversion.
"""

from __future__ import annotations

from typing import Any


class RichMessage:
    """A data-only incoming rich message representation."""

    def __init__(self, raw: dict[str, Any] | None) -> None:
        self.raw = raw or {}
        self.mode = self._detect_mode(self.raw)

    @staticmethod
    def _detect_mode(raw: dict[str, Any]) -> str | None:
        # Incoming Telegram RichMessage currently exposes block content.
        # html and markdown are InputRichMessage fields and must not be
        # inferred as incoming modes here.
        return "blocks" if "blocks" in raw else None

    def to_dict(self) -> dict[str, Any]:
        return self.raw