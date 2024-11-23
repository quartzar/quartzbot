import asyncio
import logging
import os
from argparse import ArgumentParser, Namespace

from rich.console import Console
from rich.logging import RichHandler

from src.bot import QuartzBot

rich_handler = RichHandler(
    console=Console(width=100),
    markup=True,
    rich_tracebacks=True,
    enable_link_path=False,
)

logging.basicConfig(level="INFO", format="%(message)s", datefmt="[%X]", handlers=[rich_handler])

log = logging.getLogger("rich")


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


def parse_args() -> Namespace:
    parser = ArgumentParser(description="quartzbot - A Discord bot for managing crystals")
    parser.add_argument(
        "--guild",
        "-g",
        help="Sync commands to guild specified by GUILD_ID in .env file instead of globally",
        action="store_true",
        default=False,
    )

    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main())
