"""Admin/Development functionality only"""

import asyncio
import logging
import os

from discord import Client, Interaction, app_commands
from discord.ext.commands import Cog

from src.models import PersistentMessage

log = logging.getLogger(__name__)


def is_owner():
    """Check if the user is authorised to use admin commands"""

    async def predicate(interaction: Interaction) -> bool:
        admin_users = os.getenv("ADMIN_USERS", "").split(",")
        return str(interaction.user.id) in admin_users

    return app_commands.check(predicate)


class AdminCog(Cog):
    def __init__(self, bot: Client):
        self.bot = bot
        self._watcher_task = None

    @app_commands.command()
    @is_owner()
    async def check_persistent(self, interaction: Interaction):
        """Check current persistent message configuration"""
        config = await PersistentMessage.get_or_none(
            channel__id=interaction.channel_id, guild__id=interaction.guild_id
        ).prefetch_related("message", "channel", "guild")

        if config:
            await interaction.response.send_message(
                f"Current config:\n"
                f"Guild: {config.guild.name} ({config.guild.id})\n"
                f"Channel: {config.channel.name} ({config.channel.id})\n"
                f"Message: {config.message.id}\n"
                f"Last updated: {config.last_updated}",
                ephemeral=False,
            )
        else:
            await interaction.response.send_message(
                "No persistent message configured for this channel", ephemeral=False
            )

    @app_commands.command()
    async def get_database_models(self, interaction: Interaction):
        """Get description of all database models"""
        try:
            models = await self.bot.db.describe_all_models()
            await interaction.response.send_message(f"```{models}```", ephemeral=True)
        except Exception as e:
            log.error(f"[red]Error checking database models: {str(e)}[/]")
            await interaction.response.send_message(
                f"❌ Error checking database model: {str(e)}", ephemeral=True
            )

    # @app_commands.checks.has_permissions(administrator=True)
    # @app_commands.command()
    # @is_owner()
    # async def set_persistent_channel(self, interaction: Interaction):
    #     """Set current channel as the persistent message channel"""
    #     try:
    #         # Initialise store if not already done
    #         if not hasattr(self.bot, "store"):
    #             self.bot.store = PersistentStore()
    #
    #         # First save config without message ID
    #         await self.bot.store.set_persistent_message(
    #             str(interaction.guild_id), str(interaction.channel_id)
    #         )
    #
    #         # Send initial message
    #         message = await interaction.channel.send(
    #             "This is a persistent message that will be updated!"
    #         )
    #
    #         # Update config with message ID
    #         await self.bot.store.set_persistent_message(
    #             str(interaction.guild_id), str(interaction.channel_id), str(message.id)
    #         )
    #
    #         await interaction.response.send_message(
    #             "✅ Persistent message channel set!",
    #             # ephemeral=True
    #         )
    #
    #     except Exception as e:
    #         log.exception("Failed to set persistent channel: %s", str(e))
    #         await interaction.response.send_message(
    #             "❌ Failed to set persistent channel",
    #             # ephemeral=True
    #         )

    @app_commands.command()
    @is_owner()
    async def reload_cogs(self, interaction: Interaction):
        """ADMIN ONLY: Manually reload all cogs"""
        try:
            await interaction.response.defer(ephemeral=True)
            await self.bot.reloader.load_cogs()
            await interaction.followup.send("✅ All cogs reloaded successfully!", ephemeral=True)
        except Exception as e:
            log.error(f"[red]Error reloading cogs: {str(e)}[/]")
            await interaction.followup.send(f"❌ Error reloading cogs: {str(e)}", ephemeral=True)

    @app_commands.command()
    @is_owner()
    async def toggle_autoreload(self, interaction: Interaction):
        """ADMIN ONLY: Toggle automatic cog reloading"""
        try:
            if not self._watcher_task or self._watcher_task.done():
                # Start watching
                self._watcher_task = asyncio.create_task(self.bot.reloader.start_watching())
                await interaction.response.send_message("✅ Autoreload enabled", ephemeral=True)
                log.info("[green]Autoreload enabled[/]")
            else:
                # Stop watching
                self._watcher_task.cancel()
                try:
                    await self._watcher_task
                except asyncio.CancelledError:
                    pass
                self._watcher_task = None
                await interaction.response.send_message("✅ Autoreload disabled", ephemeral=True)
                log.info("[yellow]Autoreload disabled[/]")
        except Exception as e:
            log.error(f"[red]Error toggling autoreload: {str(e)}[/]")
            await interaction.response.send_message(
                f"❌ Error toggling autoreload: {str(e)}", ephemeral=True
            )

    @app_commands.command()
    @is_owner()
    async def reload_status(self, interaction: Interaction):
        """ADMIN ONLY: Check autoreload status"""
        status = "enabled" if self._watcher_task and not self._watcher_task.done() else "disabled"
        await interaction.response.send_message(
            f"Autoreload is currently **{status}**", ephemeral=True
        )
