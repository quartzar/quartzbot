import logging

from discord import Client, Interaction, app_commands, ui
from discord.ext import commands

from src.cogs.text.views import DynamicButton

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

    # @app_commands.command()
    # async def presence(self, interaction: Interaction):
    #     # activity = Activity(type=ActivityType.streaming, name="the crystals grow")
    #     # streaming = discord.Streaming(name="the crystals grow", url="https://www.youtube.com/watch?v=B1rmDe4Kfic", platform="YouTube", detail="blah blah")
    #     # await self.bot.change_presence(activity=streaming)
    #
    #     # activity = Activity(type=ActivityType.custom, name="the crystals grow", url="https://www.youtube.com/watch?v=B1rmDe4Kfic")
    #     # activity = discord.CustomActivity(name="the crystals grow", url="https://www.youtube.com/watch?v=B1rmDe4Kfic")
    #
    #     # activity = discord.Streaming(name="bob ross", url="https://www.youtube.com/watch?v=B1rmDe4Kfic", platform="YouTube", created_at=datetime.now())
    #     # activity = Activity(
    #     #     name="the crystals grow",
    #     #     url="https://www.youtube.com/watch?v=B1rmDe4Kfic",
    #     #     platform="YouTube",
    #     #     created_at=datetime.now(),
    #     # )
    #     # activity = Activity(
    #     #     type=ActivityType.playing,
    #     #     name="YouTube Music",
    #     #     state=f"Playing the song",
    #     #     details="via quartzbot",
    #     #     timestamps={
    #     #         "start": 1621234567,
    #     #         "end": 1621235567
    #     #     },
    #     #     url="https://www.youtube.com/watch?v=B1rmDe4Kfic"
    #     # )
    #     await self.bot.change_presence(**Activities.shutdown())

    @app_commands.command()
    async def dynamic_button(self, interaction: Interaction):
        """Create a dynamic button"""

        view = ui.View(timeout=None)
        view.add_item(DynamicButton(interaction.user.id))

        await interaction.response.send_message("Here is your button", view=view)
