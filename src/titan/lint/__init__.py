"""
titan.lint

محرك Design Linter الداخلي لـ Titan.

لا يُستهلك مباشرة في الغالب — نقطة الدخول العامة هي:

    findings = bot.lint()

لكن LintFinding مُصدَّرة للـ type annotations:

    from titan.lint import LintFinding

راجع docs/decisions/012-design-linter.md.
"""

from titan.lint.engine import run_lint
from titan.lint.findings import LintFinding

__all__ = ["LintFinding", "run_lint"]
