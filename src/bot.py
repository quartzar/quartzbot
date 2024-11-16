import argparse
import asyncio
import logging
import os
import re
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from pytubefix import YouTube
from rich.logging import RichHandler

from src.cache import AudioCache
from src.utils import human_time_duration

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(markup=True, rich_tracebacks=True)],
)

log = logging.getLogger("rich")


class QuartzBot(discord.Client):
    def __init__(self, guild_id: Optional[str] = None):
        self.guild_id = guild_id
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True

        super().__init__(intents=intents)

        # Create the command tree for slash commands
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        """Called when the bot is starting up"""
        log.info(f"Logged in as [bold bright_green]{self.user}[/] (ID: {self.user.id})")

        # Add cogs
        cog = QuartzCog(self)

        # Get all app commands from the cog
        for command in cog.__cog_app_commands__:
            self.tree.add_command(command)

        # Get current command count
        total_commands = len(list(self.tree.walk_commands()))

        # Sync commands with Discord
        log.info("Syncing commands...")

        # Sync commands to the guild specified by GUILD_ID
        try:
            if self.guild_id:
                # Guild-specific sync with command clear
                guild = discord.Object(id=self.guild_id)
                self.tree.clear_commands(guild=guild)
                # await self.tree.sync(guild=guild)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                log.info(
                    f"[green]Synced {len(synced)} commands to guild: {self.guild_id} "
                    f"({total_commands} total commands)[/]"
                )
            else:
                # Global sync with command clear
                self.tree.clear_commands(guild=None)
                synced = await self.tree.sync()
                log.info(
                    f"[green]Synced {len(synced)} commands globally "
                    f"({total_commands} total commands)[/]"
                )

        except discord.errors.Forbidden as e:
            log.error(f"[red]Failed to sync commands: {e}[/]")
        except Exception as e:
            log.error(f"[red]Unexpected error syncing commands: {e}[/]")

    async def on_ready(self):
        """Called when the bot is ready and connected"""
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="the crystals grow")
        )
        log.info("[bold bright_green]quartzbot is ready![/]")


class QuartzCog(commands.Cog):
    def __init__(self, bot: QuartzBot):
        self.bot = bot
        self.cache = AudioCache()
        self.download_progress = {}
        self.FFMPEG_OPTIONS = {
            "options": "-vn",  # Disable video
        }

    """"""

    @app_commands.command()
    async def ping(self, interaction: discord.Interaction):
        """Check the bot's latency"""
        log.info("Command [underline]/ping[/] called")
        await interaction.response.send_message(
            f"Pong! Latency: {round(self.bot.latency * 1000)}ms"
        )

    """"""

    @app_commands.command()
    async def greet(
        self, interaction: discord.Interaction, name: str, greeting_type: Optional[str] = "Hello"
    ):
        """Get a 'friendly' greeting"""
        await interaction.response.send_message(f"{greeting_type}, {name}! Terrible to meet you!")

    """"""

    @app_commands.command()
    async def join(self, interaction: discord.Interaction):
        """Join the user's voice channel"""
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
        except discord.ClientException:
            await interaction.response.send_message(
                "I'm already in a voice channel you blithering mongoose!", ephemeral=False
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Failed to join: {str(e)}. Or just chose not to...", ephemeral=False
            )

    """"""

    @app_commands.command()
    async def leave(self, interaction: discord.Interaction):
        """Leave the voice channel"""
        if not interaction.guild.voice_client:
            await interaction.response.send_message("I'm not in a voice channel!", ephemeral=False)
            return

        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("Left the voice channel!", ephemeral=False)

    """"""

    @app_commands.command()
    async def stop(self, interaction: discord.Interaction):
        """Stop playing audio"""
        if not interaction.guild.voice_client:
            await interaction.response.send_message("I'm not playing anything!", ephemeral=False)
            return

        interaction.guild.voice_client.stop()
        await interaction.response.send_message("Stopped playing audio", ephemeral=False)

    """"""

    @app_commands.command()
    async def play(self, interaction: discord.Interaction, url: str, give_me_file: bool = False):
        """Play audio from YouTube URL"""
        log.info(f"Command [underline]/play[/] called with URL: [underline]{url}[/]")

        if not interaction.user.voice:
            await interaction.response.send_message(
                "You need to be in a voice channel first!", ephemeral=False
            )
            return

        video_id = re.search(
            r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})',
            url,
        )
        if not video_id:
            await interaction.response.send_message("Invalid YouTube URL", ephemeral=False)
            log.info(f"Invalid YouTube URL: {url} ")
            return

        video_id = video_id.group(1)

        try:
            await interaction.response.defer(ephemeral=False)

            # Check cache first
            audio_data = self.cache.get_audio(video_id)
            title = self.cache.get_title(video_id)

            yt = None
            if not audio_data:
                # Download if not cached
                yt = YouTube(url, on_progress_callback=self.on_progress)
                title = yt.title

                # Download directly to temp directory for initial download
                stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()
                log.info(f"Highest quality audio stream found: {stream}")
                temp_download_path = os.path.join(self.cache.temp_dir, f"download_{video_id}.m4a")

                # Initialize progress tracking
                self.download_progress[video_id] = {
                    "stream": stream,
                    "completed": False,
                    "percent": 0,
                }

                # Start download
                stream.download(output_path=self.cache.temp_dir, filename=f"download_{video_id}")

                # Wait for download to complete
                if not await self.wait_for_download(video_id):
                    raise TimeoutError("Download timed out")

                # Verify file exists
                if not os.path.exists(temp_download_path):
                    raise FileNotFoundError(f"Downloaded file not found: {temp_download_path}")

                log.info(f"Download completed: {temp_download_path}")

                # Read the file into Redis and delete the temp download file
                with open(temp_download_path, "rb") as f:
                    audio_data = f.read()
                os.unlink(temp_download_path)
                log.info("Temporary download file deleted")

                self.cache.cache_audio(video_id, audio_data)
                self.cache.cache_title(video_id, title)

            else:
                yt = YouTube(url)

            # Extract from cache to temp file only for playback
            temp_playback_path = os.path.join(self.cache.temp_dir, f"play_{video_id}.m4a")
            log.info(f"Extracting audio to temporary playback file: {temp_playback_path}")
            with open(temp_playback_path, "wb") as f:
                f.write(audio_data)

            try:
                # Connect to voice
                voice_channel = interaction.user.voice.channel
                voice_client = interaction.guild.voice_client

                if voice_client is None:
                    voice_client = await voice_channel.connect()
                elif voice_client.channel != voice_channel:
                    await voice_client.move_to(voice_channel)

                # Play audio
                if voice_client.is_playing():
                    voice_client.stop()

                def cleanup(error):
                    try:
                        if os.path.exists(temp_playback_path):
                            os.unlink(temp_playback_path)
                            log.info(f"Cleaned up temporary playback file: {temp_playback_path}")
                    except Exception as e:
                        log.error(f"Cleanup error: {e}")
                    if error:
                        log.error(f"Player error: {error}")

                voice_client.play(discord.FFmpegOpusAudio(temp_playback_path, **self.FFMPEG_OPTIONS), after=cleanup)

                await interaction.followup.send(
                    f"[**`Now playing:`** ***`{title}`***]({yt.embed_url})\n"
                    f"`Author: {yt.author}` | `Length: {human_time_duration(yt.length)}`\n"
                    f"`Uploaded: {yt.publish_date}` | `Views: {yt.views}`"
                )
                if give_me_file:
                    await interaction.followup.send(file=discord.File(temp_playback_path, filename=f"{title}.m4a"))

            except Exception as e:
                # Clean up temp playback file if voice connection fails
                if os.path.exists(temp_playback_path):
                    os.unlink(temp_playback_path)
                raise e

        except Exception as e:
            await interaction.followup.send(
                f"An error occurred: {str(e)}",
            )
            log.error(f"An error occurred during [underline]/play[/] command: {e}")

    async def wait_for_download(self, video_id: str, timeout: int = 30) -> bool:
        """Wait for download to complete"""
        start_time = asyncio.get_event_loop().time()

        while True:
            if video_id in self.download_progress:
                if self.download_progress[video_id]["completed"]:
                    del self.download_progress[video_id]
                    return True

            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                return False

            await asyncio.sleep(0.1)

    def on_progress(self, stream, chunk: bytes, bytes_remaining: int):
        """Callback for download progress"""
        # Get video_id from our stored progress data
        total_size = stream.filesize
        bytes_downloaded = total_size - bytes_remaining

        # Find the video_id from the progress dict that matches this stream
        for video_id, data in self.download_progress.items():
            if data.get("stream") == stream:
                self.download_progress[video_id].update(
                    {
                        "completed": bytes_downloaded >= total_size,
                        "percent": (bytes_downloaded / total_size) * 100,
                    }
                )
                log.info(f"Download progress: {self.download_progress[video_id]['percent']:.1f}%")
                break

    """"""


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
