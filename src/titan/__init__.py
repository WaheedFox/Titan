from importlib.metadata import version, PackageNotFoundError

from titan.bot import Titan
from titan.errors import TitanError
from titan.telegram import TelegramError
from titan.keyboard import InlineKeyboard, InlineButton
from titan.router import Router
from titan.health.models import HealthFinding, HealthLevel
from titan.inspector import BotSnapshot

try:
    __version__ = version("titanx")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = [
    "Titan",
    "TitanError",
    "TelegramError",
    "InlineKeyboard",
    "InlineButton",
    "Router",
    "HealthFinding",
    "HealthLevel",
    "BotSnapshot",
    "__version__",
]
