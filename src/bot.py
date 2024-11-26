import asyncio
import logging
from typing import cast

from discord import (
    Client,
    Intents,
    Interaction,
    Message,
    app_commands,
    errors as dc_errors,
)
from discord.app_commands import Command, ContextMenu

from src.activities import Activities
from src.cogs.dashboard.cog import DashboardCog
from src.cogs.dashboard.views import DashboardView
from src.database import Database
from src.reloader import CogReloader

log = logging.getLogger(__name__)


class QuartzBot(Client):
    def __init__(self):
        intents = Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.voice_states = True

        super().__init__(intents=intents)

        # Create the command tree for slash commands
        self.tree = app_commands.CommandTree(self)

        # Initialise reloader
        self.reloader = CogReloader(self)

        # Initialise database
        self.db = Database(self)

    async def setup_hook(self):
        """Called when the bot is starting up"""
        log.info(f"Logged in as [bold bright_green]{self.user}[/] (ID: {self.user.id})")

        # Load all cogs using reloader
        await self.reloader.load_cogs()

        # Set up database and generate schemas
        await self.db.init()

        # Add the dashboard view (if dashboard cog is loaded)
        if "dashboard" in self.reloader.cogs:
            log.info("Adding dashboard view...")
            self.add_view(DashboardView(self))

        # Start watching for changes
        asyncio.create_task(self.reloader.start_watching())

    async def on_ready(self):
        """Called when the bot is ready and connected"""
        await self.change_presence(**Activities.default())
        log.info("[bold bright_green]quartzbot is ready![/]")

        # Update the dashboard, if exists and PersistentMessage set for guild
        from typing import cast

        if dashboard_cog := cast(DashboardCog, self.reloader.cogs.get("dashboard")):
            log.info("Updating dashboard...")
            await dashboard_cog.dashboard_load()

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
            f"Command [underline]/{command.name}[/] completed.\n"
            f"➞ User:    [bold]{interaction.user.name}[/] ({interaction.user.id})\n"
            f"➞ Guild:   [bold]{interaction.guild.name}[/] ({interaction.guild.id})\n"
            f"➞ Channel: [bold]{interaction.channel.name}[/] ({interaction.channel.id})"
        )

    async def on_message(self, message: Message):
        """Called when a message is sent in any channel"""
        log.info("[dim italic]New message: %s", message.content)

        # Get dashboard cog and check message
        if dashboard_cog := cast(DashboardCog, self.reloader.cogs["dashboard"]):
            await dashboard_cog.check_message(message)

    async def on_message_delete(self, message: Message):
        """Called when a message is deleted in any channel"""
        # Get dashboard cog and check message
        log.info("[dim italic]Message deleted: %s", message.content)
        if message.author.id == self.user.id:
            log.info("[dim italic]Ignoring message delete from self")
            return
        #
        if dashboard_cog := cast(DashboardCog, self.reloader.cogs["dashboard"]):
            await dashboard_cog.check_message(message, was_deleted=True)

    # @staticmethod
    # async def on_typing(channel: abc.Messageable, user: User | Member, when: datetime):
    #     """Called when a user starts typing in a channel"""
    #     log.info("%s is typing in %s", user, channel)
    #     # Send a message to the channel the user is typing in
    #     await channel.send(f"{user.mention} is typing...")
