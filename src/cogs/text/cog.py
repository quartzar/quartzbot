import logging

from discord import Client, Interaction, app_commands
from discord.ext import commands

log = logging.getLogger(__name__)


class TextCog(commands.Cog):
    def __init__(self, bot: Client):
        self.bot = bot

    """"""

    @app_commands.command()
    async def ping(self, interaction: Interaction):
        """Check the bot's latency"""
        log.info("Command [underline]/ping[/] called")

        await interaction.response.send_message(
            f"# P O N G\n**`Latency: {round(self.bot.latency * 1000)}ms`**"
        )

    """"""

    @app_commands.command()
    async def greet(self, interaction: Interaction, name: str, greeting_type: str = "Hello"):
        """Get a 'friendly' greeting

        :param interaction:
        :param name: Who to greet?
        :param greeting_type: What to open with? Defaults to "Hello"
        """
        await interaction.response.send_message(f"{greeting_type}, {name}! Terrible to meet you!")

    """"""
