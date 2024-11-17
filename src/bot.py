import logging
from typing import Optional

import discord
from discord import app_commands

from src.cogs.music.cog import MusicCog
from src.cogs.text.cog import TextCog
from src.cogs.voice.cog import VoiceCog

log = logging.getLogger(__name__)


class QuartzBot(discord.Client):
    def __init__(self, guild_id: Optional[str] = None):
        self.guild_id = guild_id
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True

        super().__init__(intents=intents)

        # Create the command tree for slash commands
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        """Called when the bot is starting up"""
        log.info(f"Logged in as [bold bright_green]{self.user}[/] (ID: {self.user.id})")

        # Get all cogs and add their commands
        cogs = [
            MusicCog(self),
            TextCog(self),
            VoiceCog(self),
        ]
        for cog in cogs:
            for command in cog.__cog_app_commands__:
                self.tree.add_command(command)

        # Get current command count
        total_commands = len(list(self.tree.walk_commands()))

        # Sync commands to the guild specified by GUILD_ID
        log.info("Syncing commands...")
        try:
            if self.guild_id:
                # Guild-specific sync with command clear
                guild = discord.Object(id=self.guild_id)
                self.tree.clear_commands(guild=guild)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                log.info(
                    f"[green]Synced {len(synced)} commands to guild: {self.guild_id} "
                    f"({total_commands} total commands)[/]"
                )
            else:
                # Global sync with command clear
                self.tree.clear_commands(guild=None)
                synced = await self.tree.sync()
                log.info(
                    f"[green]Synced {len(synced)} commands globally "
                    f"({total_commands} total commands)[/]"
                )

        except discord.errors.Forbidden as e:
            log.error(f"[red]Failed to sync commands: {e}[/]")
        except Exception as e:
            log.error(f"[red]Unexpected error syncing commands: {e}[/]")

    async def on_ready(self):
        """Called when the bot is ready and connected"""
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="the crystals grow")
        )
        log.info("[bold bright_green]quartzbot is ready![/]")
