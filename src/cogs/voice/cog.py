import logging

from discord import Client, ClientException, Interaction, app_commands
from discord.ext import commands

log = logging.getLogger(__name__)


class VoiceCog(commands.Cog):
    def __init__(self, bot: Client):
        self.bot = bot

    @app_commands.command()
    async def join(self, interaction: Interaction):
        """Join the user's voice channel"""
        await self.__join(interaction)

    async def __join(self, interaction: Interaction):
        if not interaction.user.voice:
            await interaction.response.send_message(
                "you twit, get in a voice channel first!", ephemeral=False
            )
            return

        voice_channel = interaction.user.voice.channel

        try:
            await voice_channel.connect()
            await interaction.response.send_message(
                f"Joined {voice_channel.name}!", ephemeral=False
            )
        except ClientException:
            await interaction.response.send_message(
                "I'm already in a voice channel you blithering mongoose!", ephemeral=False
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Failed to join: {str(e)}. Or just chose not to...", ephemeral=False
            )

    """"""

    @app_commands.command()
    async def leave(self, interaction: Interaction):
        """Leave the voice channel"""
        if not interaction.guild.voice_client:
            await interaction.response.send_message("I'm not in a voice channel!", ephemeral=False)
            return

        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("Left the voice channel!", ephemeral=False)

    """"""
