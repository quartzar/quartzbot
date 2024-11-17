"""Utility functions"""
import logging
from dataclasses import dataclass

from discord import Client
from discord.ext.autoreload import Reloader

log = logging.getLogger(__name__)

TIME_DURATION_UNITS = (
    ("week", 60 * 60 * 24 * 7),
    ("day", 60 * 60 * 24),
    ("hour", 60 * 60),
    ("min", 60),
    ("sec", 1),
)


@dataclass
class QueueItem:
    video_id: str
    title: str
    requested_by: str
    url: str


def human_time_duration(seconds: int) -> str:
    if seconds == 0:
        return "inf"
    parts = []
    for unit, div in TIME_DURATION_UNITS:
        amount, seconds = divmod(int(seconds), div)
        if amount > 0:
            parts.append("{} {}{}".format(amount, unit, "" if amount == 1 else "s"))
    return ", ".join(parts)


class QuartzReloader(Reloader):
    def __init__(self, bot: Client, ext_directory: str):
        log.info(f"Initializing QuartzReloader with directory: {ext_directory}")
        super().__init__(ext_directory=ext_directory)
        self.bot = bot

    def start(self):
        """Override start method to add logging"""
        log.info("Starting QuartzReloader...")
        # Note: We don't pass self.bot here since we already have it from __init__
        super().start(self.bot)
        log.info("QuartzReloader started successfully")

    async def on_reload(self, extension: str):
        """Called when an extension is reloaded"""
        log.info(f"[yellow]on_reload called for extension: {extension}[/]")

    async def on_error(self, extension: str, error: Exception):
        """Called when an extension fails to reload"""
        log.error(f"[red]on_error called for extension {extension}: {str(error)}[/]")