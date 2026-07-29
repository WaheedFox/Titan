"""
titan.privacy

User Data lifecycle — Registry, Module Protocol, and reserved command handlers.

ADR-015: Data Lifecycle Responsibility
ADR-016: User Data Registry & erase_user
ADR-017: Reserved Privacy Commands (/mydata, /forgetme)
"""

from titan.privacy.protocol import UserDataModule
from titan.privacy.registry import UserDataRegistry

__all__ = ["UserDataModule", "UserDataRegistry"]
