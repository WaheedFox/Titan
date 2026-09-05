from importlib.metadata import version, PackageNotFoundError

from titan.bot import Titan
from titan.errors import TitanError
from titan.telegram import TelegramError
from titan.keyboard import InlineKeyboard, InlineButton
from titan.router import Router
from titan.health.models import HealthFinding, HealthLevel
from titan.inspector import BotSnapshot
from titan.rich import RichContent

try:
    __version__ = version("titan-framework")
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
    "RichContent",
    "__version__",
]
