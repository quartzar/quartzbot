import argparse
import asyncio
import logging
import os
from typing import Optional

import discord
from discord import app_commands
from dotenv import load_dotenv
from rich.logging import RichHandler

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(markup=True, rich_tracebacks=True)],
)

log = logging.getLogger("rich")

load_dotenv()


class QuartzBot(discord.Client):
    def __init__(self, guild_id: Optional[str] = None):
        self.guild_id = guild_id
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(intents=intents)

        # Create the command tree for slash commands
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        """Called when the bot is starting up"""
        log.info(f"Logged in as {self.user} (ID: {self.user.id})")

        # Add cogs
        await self.add_cog(QuartzCog(self))

        # Sync commands with Discord
        log.info("Syncing commands...")
        guild = discord.Object(id=self.guild_id) if self.guild_id else None
        await self.tree.sync(guild=guild)
        log.info("Commands synced!")

    async def on_ready(self):
        """Called when the bot is ready and connected"""
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="the crystals grow")
        )
        log.info("[bold bright_green]quartzbot is ready![/]")

    async def add_cog(self, cog):
        """Helper method to add cogs since we're not using commands.Bot"""
        for cmd in cog.commands:
            self.tree.add_command(cmd)


class QuartzCog:
    def __init__(self, bot: QuartzBot):
        self.bot = bot
        self.commands = [
            app_commands.Command(
                name="ping", description="Check the bot's latency", callback=self.ping
            ),
            app_commands.Command(
                name="greet", description="Get a friendly greeting", callback=self.greet
            ),
        ]

    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Pong! Latency: {round(self.bot.latency * 1000)}ms"
        )

    async def greet(
        self, interaction: discord.Interaction, name: str, greeting_type: Optional[str] = "Hello"
    ):
        await interaction.response.send_message(f"{greeting_type}, {name}! Nice to meet you!")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="quartzbot - A Discord bot for managing crystals")
    parser.add_argument(
        "--guild",
        "-g",
        help="Sync commands to guild specified by GUILD_ID in .env file instead of globally",
        action="store_true",
        default=False,
    )

    return parser.parse_args()


async def main():
    args = parse_args()
    guild_id = None

    # Check if guild mode was enabled
    if args.guild:
        log.info("[blue]Guild mode enabled[/]")
        guild_id = os.getenv("GUILD_ID")

    # Create bot instance
    bot = QuartzBot(guild_id=guild_id)

    # Get token from environment
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("No Discord token found. Set DISCORD_TOKEN environment variable.")

    # Start the bot
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
