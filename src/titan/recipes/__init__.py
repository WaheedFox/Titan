# ﷽
# Licensed under W.A.S.L v1.0 — github.com/WaheedFox/Titan
"""
titan.recipes

Official patterns built on top of the Titan core.

Recipes are optional. Importing titan alone carries no recipe machinery.
Each recipe is a real example of how to use the existing Titan APIs correctly —
not a new layer on top of them.

    Recipes teach the Core. They never replace the Core.

Available:
    Welcome — the recommended pattern for greeting new group members
"""

from titan.recipes.welcome import Welcome

__all__ = ["Welcome"]
