# ﷽
# Licensed under W.A.S.L v1.0 — github.com/WaheedFox/Titan
"""
titan.extras

Opt-in developer-experience utilities built on top of the Titan core.
Nothing here is imported or executed unless the developer explicitly imports
this module.

Each utility lives in its own module:
    titan.extras.alias  →  AliasMap
    titan.extras.ask    →  AskManager

Both can be imported directly from the package for convenience:
    from titan.extras import AliasMap, AskManager
"""

from titan.extras.alias import AliasMap
from titan.extras.ask import AskManager

__all__ = ["AliasMap", "AskManager"]
