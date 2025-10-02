"""Convenience methods for creating Activity instances"""

import time
from dataclasses import dataclass

from discord import Activity, ActivityType, Status


@dataclass
class Activities:
    """Collection of bot activities"""

    @staticmethod
    def default() -> dict:
        """Default watching activity"""
        return {
            "activity": Activity(
                type=ActivityType.watching,
                name="the crystals grow",
                url="https://github.com/quartzar/quartzbot",
                state_url="https://github.com/quartzar/quartzbot",
            ),
            "status": Status.online,
        }

    @staticmethod
    def youtube(title: str, url: str, author: str, application_id: int) -> dict:
        """YouTube streaming activity

        :param title: The title of the video/song
        :param url: The URL of the video/song
        :param author: The author/uploader of the video/song
        :param application_id: Your bot's application ID (client ID)

        :returns: dict suitable for passing to ``bot.change_presence(**dict)``
        """
        return {
            "activity": Activity(
                type=ActivityType.streaming,
                name=title,
                url=url,
                details=f"By {author}",
                state="via quartzbot",
                application_id=application_id,
                timestamps={"start": int(time.time())},
                assets={
                    "large_image": "youtube_logo",
                    "large_text": "Playing from YouTube",
                    "small_image": "play_icon",
                    "small_text": "Playing",
                },
                buttons=["Watch on YouTube"],
            ),
            "status": Status.online,
        }

    @staticmethod
    def cog_reload(cog_name: str) -> dict:
        return {
            "activity": Activity(type=ActivityType.watching, name=f"{cog_name} cog reload"),
            "status": Status.dnd,
        }

    @staticmethod
    def shutdown() -> dict:
        """Shutdown activity"""
        return {
            "activity": Activity(type=ActivityType.watching, name="myself shutdown"),
            "status": Status.dnd,
        }

    @staticmethod
    def maintenance() -> Activity:
        """Maintenance mode activity"""
        return Activity(type=ActivityType.playing, name="Maintenance Mode 🛠️")

    @staticmethod
    def error() -> Activity:
        """Error state activity"""
        return Activity(type=ActivityType.playing, name="⚠️ Error occurred")
