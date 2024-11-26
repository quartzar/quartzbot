import logging
from typing import TYPE_CHECKING

from discord import ButtonStyle, Color, Embed, Interaction, Message, ui
from discord.ui import Button, View
from pytubefix import YouTube

from src.utils import QueueItem

if TYPE_CHECKING:
    from src.bot import QuartzBot

log = logging.getLogger(__name__)


class DashboardView(View):
    def __init__(self, bot: "QuartzBot"):
        super().__init__(timeout=None)  # Persistent view should never time out
        self.bot = bot

    @ui.button(label="𝗣𝗟𝗔𝗬 / 𝗣𝗔𝗨𝗦𝗘", style=ButtonStyle.success, custom_id="dashboard:playpause")
    async def playpause(self, interaction: Interaction, button: Button):
        """Toggle play/pause"""

        # Get music cog
        music_cog = self.bot.reloader.cogs["music"]
        if not music_cog:
            return await interaction.response.send_message(
                "Music system not available", ephemeral=False
            )

        if not music_cog.currently_playing:
            return await interaction.response.send_message("Nothing is playing", ephemeral=False)

        # Toggle playback
        voice_client = interaction.guild.voice_client
        if voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message("▶️ Resumed", ephemeral=False)
        else:
            voice_client.pause()
            await interaction.response.send_message("⏸️ Paused", ephemeral=False)

    @ui.button(label="𝗦𝗞𝗜𝗣", style=ButtonStyle.danger, custom_id="dashboard:skip")
    async def skip(self, interaction: Interaction, button: Button):
        """Skip current track"""
        if music_cog := self.bot.reloader.cogs["music"]:
            await music_cog.skip(interaction)
        else:
            return await interaction.response.send_message(
                "Music system not available", ephemeral=False
            )

    # join
    @ui.button(label="𝗝𝗢𝗜𝗡", style=ButtonStyle.primary, custom_id="dashboard:join")
    async def join(self, interaction: Interaction, button: Button):
        """Join the user's voice channel"""
        if voice_cog := self.bot.reloader.cogs["voice"]:
            await voice_cog.__join(interaction)

    @ui.button(label="𝗥𝗘𝗙𝗥𝗘𝗦𝗛", style=ButtonStyle.secondary, custom_id="dashboard:refresh")
    async def refresh(self, interaction: Interaction, button: Button):
        """Refresh the dashboard"""
        await self.update_dashboard(interaction)

    async def update_dashboard(
        self, interaction: Interaction | None = None, message: Message | None = None
    ):
        """Update dashboard content"""
        embed = Embed(title="𝗗𝗮𝘀𝗵𝗯𝗼𝗮𝗿𝗱 - - - - - - - - - - - - - - - - -", color=Color.green())
        embed.url = "https://github.com/quartzar/quartzbot"

        # set the small text that goes above the title
        embed.description = "```\n.oOo.oOo.oOo.oOo.oOo.oOo.```"
        # embed.description = "```\n" + "𝗤𝘂𝗮𝗿𝘁𝘇𝗕𝗼𝘁 𝗗𝗮𝘀𝗵𝗯𝗼𝗮𝗿𝗱" + "\n```"

        # embed.description = "```\n𝗗𝗮𝘀𝗵𝗯𝗼𝗮𝗿𝗱\n```"
        # set the author of the embed
        embed.set_author(
            name="𝗾𝘂𝗮𝗿𝘁𝘇𝗯𝗼𝘁",
            url="https://github.com/quartzar/quartzbot",
            icon_url="https://a.l3n.co/i/LRR5ix.th.png",
        )

        # set the footer of the embed
        embed.set_footer(text="hello there", icon_url="https://a.l3n.co/i/LRR5ix.th.png")

        # embed.set_image(url="https://a.l3n.co/i/LRR5ix.th.png")

        embed.set_thumbnail(url="https://a.l3n.co/i/LRR5ix.th.png")

        # log.info([cog for cog in self.bot.reloader.cogs])
        # log.info(self.bot.reloader.cogs["music"])
        # Add music info if available
        music_cog = self.bot.reloader.cogs["music"]
        if music_cog and music_cog.currently_playing:
            current: QueueItem = music_cog.currently_playing
            embed.add_field(
                name="Now Playing",
                value=f"🎵 {current.title}",
                inline=False,
            )
            yt = YouTube(url=current.url)
            embed.set_image(url=yt.thumbnail_url)
            if music_cog.queue:
                next_up = "\n".join(
                    f"{i+1}. {item.title}" for i, item in enumerate(list(music_cog.queue)[:3])
                )
                embed.add_field(name="Queue", value=next_up or "Empty", inline=False)
        else:
            embed.add_field(name="Music", value="No music playing", inline=False)
            embed.set_image(url=None)

        if interaction:
            await interaction.response.edit_message(embed=embed, view=self)
        elif message:
            await message.edit(embed=embed, view=self)
        return embed


class ConfirmView(View):
    def __init__(self):
        super().__init__(timeout=30)
        self.value = None

    @ui.button(label="Confirm", style=ButtonStyle.success, custom_id="dashboard:confirm:yes")
    async def confirm(self, interaction: Interaction, button: Button):
        self.value = True
        self.stop()

    @ui.button(label="Cancel", style=ButtonStyle.danger, custom_id="dashboard:confirm:no")
    async def cancel(self, interaction: Interaction, button: Button):
        self.value = False
        self.stop()
