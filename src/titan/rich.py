"""
Outgoing rich message content.

This module owns Titan's small content boundary.  Telegram-specific
serialization and network behavior belong to the request/transport layer.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


_CONSTRUCTOR_TOKEN = object()


class RichContent:
    """
    A typed outgoing rich content value.

    Values are created through one of the explicit mode constructors:
    ``html``, ``markdown``, or ``blocks``.
    """

    __slots__ = ("_mode", "_representation")

    def __init__(
        self,
        *,
        _mode: str,
        _representation: Any,
        _token: object | None = None,
    ) -> None:
        if _token is not _CONSTRUCTOR_TOKEN:
            raise TypeError(
                "RichContent must be created with html(), markdown(), or blocks()."
            )

        self._mode = _mode
        self._representation = _representation

    @classmethod
    def html(cls, markup: str) -> RichContent:
        """Create HTML rich content."""
        if not isinstance(markup, str):
            raise TypeError("RichContent.html() requires a string markup value.")

        return cls(
            _mode="html",
            _representation=markup,
            _token=_CONSTRUCTOR_TOKEN,
        )

    @classmethod
    def markdown(cls, markup: str) -> RichContent:
        """Create Markdown rich content."""
        if not isinstance(markup, str):
            raise TypeError("RichContent.markdown() requires a string markup value.")

        return cls(
            _mode="markdown",
            _representation=markup,
            _token=_CONSTRUCTOR_TOKEN,
        )

    @classmethod
    def blocks(cls, blocks: Sequence[Mapping[str, Any]]) -> RichContent:
        """Create rich block content after validating its basic shape."""
        if (
            isinstance(blocks, (str, bytes, Mapping))
            or not isinstance(blocks, Sequence)
        ):
            raise TypeError(
                "RichContent.blocks() requires a sequence of mappings."
            )

        for block in blocks:
            if not isinstance(block, Mapping):
                raise TypeError(
                    "RichContent.blocks() requires every block to be a mapping."
                )

        return cls(
            _mode="blocks",
            _representation=blocks,
            _token=_CONSTRUCTOR_TOKEN,
        )

    @property
    def mode(self) -> str:
        """The explicitly selected content mode."""
        return self._mode

    @property
    def representation(self) -> Any:
        """The mode-specific representation supplied by the caller."""
        return self._representation