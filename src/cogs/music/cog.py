import asyncio
import logging
import os
import re
from collections import deque

from discord import (
    Client,
    Color,
    Embed,
    FFmpegOpusAudio,
    File,
    Interaction,
    VoiceClient,
    VoiceProtocol,
    app_commands,
)
from discord.ext import commands
from pytubefix import Search, YouTube

from src.activities import Activities
from src.cache import AudioCache
from src.cogs.music.views import SongSelector
from src.utils import QueueItem, human_time_duration

FFMPEG_OPTIONS = {
    "options": "-vn",  # Disable video
}

log = logging.getLogger(__name__)


class MusicCog(commands.Cog):
    def __init__(self, bot: Client, **kwargs):
        self.bot = bot
        self.cache = AudioCache()
        self.download_progress = {}
        self.currently_playing = kwargs.get("currently_playing", None)
        self.queue = kwargs.get("queue", deque())

    """"""

    @app_commands.command()
    async def play(self, interaction: Interaction, url: str, give_me_file: bool = False):
        """Play audio from YouTube

        :param interaction: :class:`Interaction`
        :param url: Either paste a URL, or enter a word or phrase to search YouTube for results
        :param give_me_file: Option for the audio file to be sent on Discord
        """
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
            # Didn't get a URL, search instead and get first 5 results
            search = Search(url)

            results = search.videos[:7]

            if not results:
                await interaction.response.send_message("No results found!")
                return

            # Create embed with search results
            embed = Embed(
                title="🔎 Search Results",
                description=f"Found {len(results)} results for: {url}",
                color=Color.blue(),
            )

            for i, video in enumerate(results, 1):
                embed.add_field(
                    name=f"{i}. {video.title}",
                    value=f"`Duration: {human_time_duration(video.length)}`",
                    inline=False,
                )

            # Create view with selection menu
            view = SongSelector(results, self, interaction)

            await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

            # Store message reference for timeout handling
            view.message = await interaction.original_response()
            return

        # If we got here, it's a direct URL
        await self.play_from_url(interaction, url, give_me_file)

    """"""

    async def play_from_url(self, interaction: Interaction, url: str, give_me_file: bool = False):
        """Helper method to play from direct URL"""
        log.info("Running [underline]play_from_url()[/]")
        video_id = re.search(
            r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})',
            url,
        ).group(1)

        await interaction.response.defer(ephemeral=False)

        # Check cache first
        audio_data = self.cache.get_audio(video_id)
        title = self.cache.get_title(video_id)
        try:
            if not audio_data:
                # Download if not cached
                yt = YouTube(url, on_progress_callback=self.on_progress)
                title = yt.title

                # Download directly to temp directory for initial download
                stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()
                log.info(f"Highest quality audio stream found: {stream}")
                temp_download_path = os.path.join(self.cache.temp_dir, f"download_{video_id}")

                # Initialise progress tracking
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

            # Create queue item
            queue_item = QueueItem(
                video_id=video_id, title=title, requested_by=interaction.user.name, url=url
            )

            # Add to queue
            self.queue.append(queue_item)
            position = len(self.queue)

            # If nothing is playing, start playback
            voice_channel = interaction.user.voice.channel
            voice_client: VoiceClient | VoiceProtocol = interaction.guild.voice_client
            if not self.currently_playing or not voice_client.is_playing():
                await self.play_next(interaction)
            else:
                await interaction.edit_original_response(
                    content=f"> __{title}__ *added to queue at position* **{position}**",
                    embed=None,
                    view=None,
                )
                # remove original search results embed/view w/e, just want the above text:

                # await interaction.followup.send(
                #     f"Added to queue (position {position}): {title}",
                # )

            # Send the file if user requested it
            if give_me_file:
                temp_file_path = os.path.join(self.cache.temp_dir, f"play_{video_id}.m4a")
                with open(temp_file_path, "wb") as f:
                    f.write(audio_data)
                await interaction.followup.send(file=File(temp_file_path, filename=f"{title}.m4a"))
                os.unlink(temp_file_path)

        except Exception as e:
            await interaction.followup.send(
                f"An error occurred: ```\n{str(e)}\n```",
            )
            log.exception(f"An error occurred during [underline]/play[/] command: {e}")

    """"""

    @app_commands.command()
    async def skip(self, interaction: Interaction):
        """Skip current song"""
        await self.__skip(interaction)

    async def __skip(self, interaction: Interaction):
        if not interaction.guild.voice_client:
            await interaction.response.send_message(
                "Nothing is playing!",
            )
            return

        await interaction.response.send_message(
            "Skipping current song",
        )
        await self.terminate_playback(interaction.guild.voice_client)
        await self.play_next(interaction)

    """"""

    @app_commands.command()
    async def queue(self, interaction: Interaction):
        """Show current queue"""
        if not self.currently_playing and not self.queue:
            await interaction.response.send_message(
                "Nothing is playing or queued",
            )
            return

        queue_text = []
        if self.currently_playing:
            queue_text.append(
                f"🎵  Now Playing: __{self.currently_playing.title}__ `(requested by {self.currently_playing.requested_by})`"
            )

        if self.queue:
            queue_text.append("\n📋 __queue__")
            for i, item in enumerate(self.queue, 1):
                queue_text.append(f"{i}. {item.title} (requested by {item.requested_by})")

        await interaction.response.send_message(
            "\n".join(queue_text),
        )

    """"""

    @app_commands.command()
    async def pause(self, interaction: Interaction):
        """Pause the current song"""
        if not interaction.guild.voice_client:
            await interaction.response.send_message(
                "Nothing is playing!",
            )
            return

        voice_client = interaction.guild.voice_client

        if voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message(
                f"⏸️ Paused: {self.currently_playing.title}",
            )
        else:
            await interaction.response.send_message(
                "Nothing is currently playing.",
            )

    """"""

    @app_commands.command()
    async def resume(self, interaction: Interaction):
        """Resume the current song"""
        if not interaction.guild.voice_client:
            await interaction.response.send_message(
                "Nothing is paused!",
            )
            return

        voice_client = interaction.guild.voice_client

        if voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message(
                f"▶️ Resumed: {self.currently_playing.title}",
            )
        else:
            await interaction.response.send_message(
                "Nothing is currently paused.",
            )

    """"""

    @app_commands.command()
    async def stop(self, interaction: Interaction):
        """Stop playing audio"""
        if not interaction.guild.voice_client:
            await interaction.response.send_message("I'm not playing anything!", ephemeral=False)
            return

        interaction.guild.voice_client.stop()
        await interaction.response.send_message("Stopped playing audio", ephemeral=False)

    """"""

    """
    UTILITY
    """

    async def terminate_playback(self, voice_client):
        """Safely terminate current playback"""
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            # Wait a brief moment for FFmpeg to clean up
            await asyncio.sleep(0.5)
            return True
        return False

    """"""

    async def play_next(self, interaction: Interaction):
        """Play next item in queue"""
        if not self.queue:
            self.currently_playing = None
            return

        next_item = self.queue.popleft()
        await self.play_audio(interaction, next_item)

    """"""

    async def play_audio(self, interaction: Interaction, queue_item: QueueItem):
        """Handle the actual audio playback"""
        try:
            # Extract from cache to temp file only for playback
            temp_playback_path = os.path.join(
                self.cache.temp_dir, f"play_{queue_item.video_id}.m4a"
            )

            # Get audio data from cache
            audio_data = self.cache.get_audio(queue_item.video_id)
            if not audio_data:
                raise ValueError("Audio data not found in cache")

            log.info(f"Extracting audio to temporary playback file: {temp_playback_path}")
            with open(temp_playback_path, "wb") as f:
                f.write(audio_data)

            # Connect to voice
            voice_channel = interaction.user.voice.channel
            voice_client: VoiceClient | VoiceProtocol = interaction.guild.voice_client

            if voice_client is None:
                voice_client = await voice_channel.connect()
            elif voice_client.channel != voice_channel:
                await voice_client.move_to(voice_channel)

            # Update currently playing
            self.currently_playing = queue_item

            def after_playing(error):
                try:
                    if os.path.exists(temp_playback_path):
                        os.unlink(temp_playback_path)
                        log.info(f"Cleaned up temporary playback file: {temp_playback_path}")
                except Exception as e:
                    log.error(f"Cleanup error: {e}")
                if error:
                    log.error(f"Player error: {error}")

                # Schedule playing the next song
                asyncio.run_coroutine_threadsafe(self.play_next(interaction), self.bot.loop)

            # Play the audio file
            voice_client.play(
                FFmpegOpusAudio(temp_playback_path, **FFMPEG_OPTIONS),
                after=after_playing,
            )

            yt = YouTube(url=queue_item.url)

            # Construct the embed
            embed = Embed(
                title=yt.title,
                description=f"**Author:** {yt.author}\n"
                f"**Length:** {human_time_duration(yt.length)}\n"
                f"**Uploaded:** {str(yt.publish_date).split(' ')[0]}\n"
                f"**Views:** {yt.views:,}\n",
                color=Color.green(),
                url=yt.embed_url,
                timestamp=interaction.created_at,
            )

            # youtube_logo_url = "https://png.pngtree.com/png-clipart/20221018/ourmid/pngtree-youtube-social-media-3d-stereo-png-image_6308427.png"
            embed.set_thumbnail(url=yt.thumbnail_url)

            # Get the requester info
            requester = interaction.guild.get_member_named(queue_item.requested_by)
            embed.set_footer(
                text=f"Requested by {queue_item.requested_by}",
                icon_url=requester.display_avatar.url,
            )
            # embed.set_author(name=requester.display_name, url=f"https://discord.com/users/{requester.id}", icon_url=requester.display_avatar.url)
            embed.set_author(
                name="Now Playing",
                icon_url="https://cdn-icons-png.flaticon.com/512/10181/10181264.png",
            )

            # filename = f"{queue_item.video_id}_thumbnail.jpg"
            # thumbnail = await download_image_from_url(url=yt.thumbnail_url)
            # file = File(thumbnail, filename=filename)
            # embed.set_image(url=f"attachment://{filename}")

            # set embed video to the YouTube video:
            # embed.video

            # embed.set_image(url=f"attachment://{filename}")
            # requester = interaction.guild.get_member_named(queue_item.requested_by)
            # embed.set_footer(text=f"Requested by {queue_item.requested_by}", icon_url=requester.display_avatar.url)
            # embed.set_thumbnail(url=f"attachment://{filename}")
            # # get the person who requested the song from queue_item and generate a link to their Discord:
            # embed.set_author(name=requester.display_name, url=f"https://discord.com/users/{requester.id}", icon_url=requester.display_avatar.url)

            await interaction.followup.send(embed=embed)

            await self.bot.change_presence(
                **Activities.youtube(
                    title=yt.title,
                    url=yt.watch_url,
                    author=yt.author,
                    application_id=self.bot.application_id,
                )
            )

            # activity = Activity(type=Streaming, name=yt.title, url=yt.watch_url, details=yt.description, buttons=[{"label": "Watch", "url": yt.watch_url}])
            # activity = Streaming(
            #     name=yt.title, url=yt.watch_url, platform="YouTube", details=yt.description
            # )
            # await self.bot.change_presence(activity=activity)

            # await interaction.followup.send(
            #     f"[**`Now playing:`** **__`{yt.title}`__**]({yt.embed_url})\n"
            #     f"`Author: {yt.author}` | `Length: {human_time_duration(yt.length)}`\n"
            #     f"`Uploaded: {yt.publish_date}` | `Views: {yt.views}`"
            # )

        except Exception as e:
            log.error(f"Error in play_audio: {e}")
            if os.path.exists(temp_playback_path):
                os.unlink(temp_playback_path)
            raise e

    """"""

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

    """"""

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
