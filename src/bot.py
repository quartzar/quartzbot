import asyncio
import logging
from datetime import datetime

from discord import (
    Client,
    Intents,
    Interaction,
    Member,
    User,
    abc,
    app_commands,
    errors as dc_errors,
)
from discord.app_commands import Command, ContextMenu

from src.activities import Activities
from src.reloader import CogReloader

log = logging.getLogger(__name__)


class QuartzBot(Client):
    def __init__(self):
        intents = Intents.default()
        intents.message_content = True
        intents.voice_states = True

        super().__init__(intents=intents)

        # Create the command tree for slash commands
        self.tree = app_commands.CommandTree(self)

        # Initialise reloader
        self.reloader = CogReloader(self)

    async def setup_hook(self):
        """Called when the bot is starting up"""
        log.info(f"Logged in as [bold bright_green]{self.user}[/] (ID: {self.user.id})")

        # Load all cogs using reloader
        await self.reloader.load_cogs()

        # Start watching for changes
        asyncio.create_task(self.reloader.start_watching())

    async def on_ready(self):
        """Called when the bot is ready and connected"""
        await self.change_presence(**Activities.default())
        log.info("[bold bright_green]quartzbot is ready![/]")

    async def sync_commands(self):
        """Sync commands to all guilds the bot is in"""
        total_commands = len(list(self.tree.walk_commands()))

        log.info("Syncing commands...")
        try:
            # Sync to all guilds the bot is in
            async for guild in self.fetch_guilds():
                log.info("Syncing commands to guild: [bold underline]%s[/]", guild.name)
                self.tree.clear_commands(guild=guild)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                log.info(
                    "[green]Synced %d commands to guild: [bold underline]%s[/] (%d total commands)[/]",
                    len(synced),
                    guild.name,
                    total_commands,
                )

        except dc_errors.Forbidden as e:
            log.exception(f"[red]Failed to sync commands: Missing permissions - {e}[/]")
        except dc_errors.HTTPException as e:
            log.exception(f"[red]Failed to sync commands: Discord API error - {e}[/]")
        except dc_errors.DiscordException as e:
            log.exception(f"[red]Failed to sync commands: Discord-specific error - {e}[/]")
        except Exception as e:
            log.exception(f"[red]Unexpected error syncing commands: {e}[/]")

    async def on_guild_join(self, guild):
        """Called when the bot joins a guild"""
        log.info(
            "Joined guild: [b]%s[/], calling the [bold yellow underline]CogReloader[/]...",
            guild.name,
        )
        await self.reloader.load_cogs()

    @staticmethod
    async def on_app_command_completion(interaction: Interaction, command: Command | ContextMenu):
        """Called when an app command is completed"""
        log.info(
            "Command [underline]%s[/] completed with interaction [underline]%s[/]",
            command.name,
            interaction,
        )

    @staticmethod
    async def on_typing(channel: abc.Messageable, user: User | Member, when: datetime):
        """Called when a user starts typing in a channel"""
        log.info("%s is typing in %s", user, channel)
        # Send a message to the channel the user is typing in
        await channel.send(f"{user.mention} is typing...")
