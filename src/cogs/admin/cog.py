"""Admin/Development functionality only"""

import asyncio
import logging
import os

from discord import Client, Interaction, app_commands
from discord.ext.commands import Cog

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
