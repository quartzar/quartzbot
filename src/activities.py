"""Convenience methods for creating Activity instances"""

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
            ),
            "status": Status.online,
        }

    @staticmethod
    def youtube(title: str, url: str) -> Activity:
        """YouTube streaming activity"""
        return Activity(
            type=ActivityType.streaming,
            name=f"Playing {title}",
            url=url,
            state="via quartzbot",
            assets={
                "large_image": "youtube_logo",
                "large_text": "YouTube Music",
                "small_image": "play_icon",
                "small_text": "Playing",
            },
        )

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
