from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LintFinding:
    """
    نتيجة فحص معماري واحدة من bot.lint().

    level:   "WARNING" فقط في v1 — لا ERROR، لا INFO.
    code:    معرّف فريد للقاعدة مثل "TITAN_LINT_001".
    message: وصف الانتهاك المكتشف.
    hint:    اقتراح التصحيح — إلزامي دائماً.

    راجع docs/decisions/012-design-linter.md.
    """

    level: str
    code: str
    message: str
    hint: str

    def __str__(self) -> str:
        return (
            f"{self.level} [{self.code}]: {self.message}\n"
            f"  Hint: {self.hint}"
        )
