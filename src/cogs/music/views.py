import logging
from typing import TYPE_CHECKING

from discord import Interaction, SelectOption, ui

from src.utils import human_time_duration

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.cogs.music.cog import MusicCog


class SongSelector(ui.View):
    def __init__(self, results, play_command, original_interaction):
        super().__init__(timeout=30)
        self.play_command = play_command
        self.original_interaction = original_interaction
        self.add_item(SongSelect(results))

    async def on_timeout(self):
        # Disable the view when it times out
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)


class SongSelect(ui.Select):
    def __init__(self, results):
        options = [
            SelectOption(
                label=f"{result.title[:70]}...",  # Truncate long titles
                description=f"Duration: {human_time_duration(result.length)}",
                value=str(i),
                emoji="🎵",
            )
            for i, result in enumerate(results)
        ]

        super().__init__(
            placeholder="Choose a song to play...",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.results = results

    async def callback(self, interaction: Interaction):
        try:
            # Get the selected video
            selected_index = int(self.values[0])
            selected_video = self.results[selected_index]

            # Disable the select menu
            self.disabled = True
            await interaction.message.edit(view=self.view)

            await self.view.play_command.play_from_url(
                interaction=interaction, url=selected_video.watch_url
            )

        except Exception as e:
            log.error(f"Error in song selection: {e}")
            await interaction.response.send_message(
                f"Failed to play selected song: {str(e)}",
            )


class SongSearchModal(ui.Modal):
    def __init__(self, cog: "MusicCog", interaction: Interaction):
        super().__init__(
            title="𝗾.𝗯 𝗦𝗼𝗻𝗴𝗦𝗲𝗮𝗿𝗰𝗵",
            timeout=60,
            custom_id="dashboard:search:modal",
        )
        self.cog = cog
        self.interaction = interaction

    song = ui.TextInput(
        label="Enter YouTube URL or search query",
        placeholder="https://youtu.be/o-YBDTqX_ZU",
        custom_id="dashboard:search:song_input",
    )

    # TODO: Add select view with search results once implemented in Discord:
    # https://github.com/discord/discord-api-docs/discussions/5883

    async def on_submit(self, interaction: Interaction):
        if url := self.song.value:
            await self.cog._play(interaction=interaction, url=url, give_me_file=False)

    async def on_error(self, interaction: Interaction, error: Exception):
        log.exception(f"Error in song search modal: {error}")
        await interaction.response.send_message(
            f"Failed to search for song: {str(error)}",
        )
