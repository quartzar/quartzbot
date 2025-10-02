import asyncio
import logging
from typing import TYPE_CHECKING

import discord
from discord import Interaction, Message, app_commands
from discord.ext import commands

from src.cogs.admin.cog import is_owner
from src.cogs.dashboard.views import ConfirmView, DashboardView
from src.models import Channel, Guild, PersistentMessage

if TYPE_CHECKING:
    from src.bot import QuartzBot

log = logging.getLogger(__name__)


class DashboardCog(commands.Cog):
    def __init__(self, bot: "QuartzBot", **kwargs):
        self.bot = bot
        self.view = DashboardView(bot)
        self._locks = {}

    @app_commands.command(name="set-dashboard")
    @is_owner()
    async def set_dashboard(self, interaction: Interaction):
        """Set current channel as the dashboard channel"""
        log.info("Command [underline]/set_dashboard[/] called")
        try:
            # Check if this guild already has a dashboard channel
            persistent_message = await PersistentMessage.get_or_none(guild_id=interaction.guild.id)
            if not persistent_message:
                log.info("No existing dashboard channel found for the guild")
                guild = await Guild.get_or_create(
                    id=interaction.guild.id, defaults={"name": interaction.guild.name}
                )
                msg = "Guild object created" if guild[1] else "Guild already exists"
                log.info(msg)
                channel = await Channel.get_or_create(
                    id=interaction.channel.id,
                    defaults={"name": interaction.channel.name, "guild": guild[0]},
                )
                msg = "Channel object created" if channel[1] else "Channel already exists"
                log.info(msg)

                await interaction.response.send_message("✅ Setting dashboard channel...")

            elif await persistent_message.channel == interaction.channel.id:
                log.info("Channel is already set as the dashboard channel")
                await interaction.response.send_message(
                    "❌ This channel is already set as the dashboard channel"
                )
                return

            else:
                log.info(
                    "Dashboard already set for the guild, checking if user wants to overwrite..."
                )
                view = ConfirmView()
                await interaction.response.send_message(
                    "Dashboard **already exists** for this server.\n"
                    "Do you wish to **overwrite** it?",
                    view=view,
                )
                await view.wait()
                if view.value is None:
                    log.info("User did not confirm dashboard overwrite in time")
                    await interaction.edit_original_response(
                        content="❌ Dashboard overwrite timed out", view=None
                    )
                    return
                if not view.value:
                    log.info("User cancelled dashboard overwrite")
                    await interaction.edit_original_response(
                        content="❌ Dashboard overwrite cancelled", view=None
                    )
                    return
                log.info("User confirmed dashboard overwrite")
                await interaction.edit_original_response(
                    content="✅ Overwriting dashboard...", view=None
                )

                log.info("Deleting previous PersistentMessage...")
                await persistent_message.delete()
                if not await Channel.get_or_none(id=interaction.channel.id):
                    log.info("Channel not found in database, creating...")
                    await Channel.create(
                        id=interaction.channel.id,
                        name=interaction.channel.name,
                        guild_id=interaction.guild.id,
                    )
                    log.info("Channel created successfully")

            # Now we can set the dashboard channel
            log.info("Sending initial dashboard message...")
            embed = await self.view.update_dashboard()
            message = await interaction.channel.send(embed=embed, view=self.view)

            log.info("Generating new PersistentMessage record...")
            await PersistentMessage.update_or_create(
                guild_id=interaction.guild.id,
                channel_id=interaction.channel.id,
                message_id=message.id,
            )
            log.info("Dashboard channel set successfully")
            await interaction.edit_original_response(content="✅ Dashboard channel set!")

        except Exception as e:
            log.exception("Failed to set dashboard: %s", e)
            await interaction.edit_original_response(
                content=f"❌ Failed to set dashboard:\n```\n{e}\n```"
            )

    @app_commands.command(name="remove-dashboard")
    @is_owner()
    async def remove_dashboard(self, interaction: Interaction):
        """Remove the current dashboard channel"""
        try:
            log.info("Removing dashboard channel...")
            guild = await Guild.get_or_none(id=interaction.guild_id)
            channel = await Channel.get_or_none(id=interaction.channel_id)

            if not guild or not channel:
                return await interaction.response.send_message(
                    "❌ No dashboard channel found", ephemeral=False
                )

            persistent_message = await PersistentMessage.get_or_none(guild=guild, channel=channel)
            if not persistent_message:
                return await interaction.response.send_message(
                    "❌ No dashboard channel found", ephemeral=False
                )

            await persistent_message.delete()
            await interaction.response.send_message(
                "✅ Dashboard channel removed", ephemeral=False
            )

        except Exception as e:
            log.error(f"Failed to remove dashboard: {e}")
            await interaction.response.send_message(
                f"❌ Failed to remove dashboard:\n```\n{e}\n```", ephemeral=False
            )

    async def get_channel_lock(self, channel_id: int) -> asyncio.Lock:
        """Get or create a lock for a specific channel"""
        if channel_id not in self._locks:
            self._locks[channel_id] = asyncio.Lock()
        return self._locks[channel_id]

    async def dashboard_load(self):
        # Check if this guild has a message
        async for guild in self.bot.fetch_guilds():
            log.info("[dim italic]Checking guild: %s for persistent message", guild.name)
            all_persistent_messages = await PersistentMessage.all().prefetch_related(
                "channel", "guild"
            )
            log.info("[dim italic]All PersistentMessages: %s", all_persistent_messages)
            if persistent_message := await PersistentMessage.get_or_none(
                guild_id=guild.id
            ).prefetch_related("channel", "guild"):
                log.info("[dim italic]PersistentMessage found for guild: %s", guild.name)
                channel_id = persistent_message.channel.id
                message_id = persistent_message.message_id
                try:
                    if channel := await guild.fetch_channel(channel_id):
                        log.info(
                            "[dim italic]Channel found for PersistentMessage: %s", channel.name
                        )
                        try:
                            if message := await channel.fetch_message(message_id):
                                log.info(
                                    "[dim italic]Message found for PersistentMessage: %s",
                                    message.id,
                                )
                                # Check if message is latest message in channel
                                if message.id == channel.last_message_id:
                                    log.info(
                                        "[dim italic]Message is the latest message in channel, will just update view"
                                    )
                                    await self.view.update_dashboard(message=message)
                                    continue
                                else:
                                    log.info("Message is not the latest message in channel")
                            log.info("Updating message")
                            last_message = await channel.fetch_message(channel.last_message_id)
                            await self.check_message(last_message)

                        except discord.NotFound:
                            log.warning("Message %s not found in channel", message_id)

                except discord.InvalidData as e:
                    log.error("Invalid data fetching channel: %s", e)
                except discord.NotFound as e:
                    log.error("Channel not found for PersistentMessage: %s", e)
                except discord.Forbidden as e:
                    log.error("Forbidden fetching channel: %s", e)
                except discord.HTTPException as e:
                    log.error("HTTP error fetching channel: %s", e)
                except Exception as e:
                    log.exception("Unexpected error fetching channel: %s", e)

            else:
                log.info("[dim italic]No PersistentMessage found for guild: %s", guild.name)

    async def check_message(self, message: Message, was_deleted: bool = False):
        """Check if message requires persistent message update"""
        # Get lock for this channel
        lock = await self.get_channel_lock(message.channel.id)

        # Use lock to prevent concurrent updates!
        await lock.acquire()
        try:
            log.info("[dim italic]Checking if message requires PersistentMessage update...")
            persistent_message = await PersistentMessage.get_or_none(
                channel_id=message.channel.id, guild_id=message.guild.id
            )
            if not persistent_message:
                log.info("[dim italic]No PersistentMessage for this channel was found")
                return
            if persistent_message.message_id == message.id and not was_deleted:
                log.info("[dim italic]Message is the PersistentMessage (me!), skipping")
                return

            # Just do a quick check to see if persistent message is already latest...
            channel = message.channel
            latest_message = await channel.fetch_message(channel.last_message_id)
            if latest_message.id == persistent_message.message_id:
                log.info("[dim italic]PersistentMessage is already the latest message, skipping")
                return

            # Create new message
            old_message_id = persistent_message.message_id
            log.info("Creating and sending new persistent message...")
            embed = await self.view.update_dashboard()
            new_message = await message.channel.send(embed=embed, view=self.view)

            # Update database
            log.info("Updating database...")
            persistent_message.message_id = new_message.id

            # Delete old message
            try:
                log.info("Deleting old persistent message...")
                old_message = await message.channel.fetch_message(old_message_id)
                log.info("Old message ID: %s", old_message.id)
                await old_message.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
                log.error(
                    "Could not delete old message: %s with ID: %s",
                    e,
                    persistent_message.message_id,
                )
            except Exception as e:
                log.exception(
                    "Unexpected error deleting old message: %s with ID: %s",
                    e,
                    persistent_message.message_id,
                )

            # Save updated PersistentMessage to db
            await persistent_message.save()
            log.info("Persistent message updated successfully")

        except Exception as e:
            log.exception("Error checking message: %s", e)

        finally:
            # log.info("[dim italic]Sleeping for 1 second before releasing persistent message update lock...")
            await asyncio.sleep(1)
            lock.release()
