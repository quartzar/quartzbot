import logging

import discord

from src.utils import human_time_duration

log = logging.getLogger(__name__)


class SongSelector(discord.ui.View):
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


class SongSelect(discord.ui.Select):
    def __init__(self, results):
        options = [
            discord.SelectOption(
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

    async def callback(self, interaction: discord.Interaction):
        try:
            # Get the selected video
            selected_index = int(self.values[0])
            selected_video = self.results[selected_index]

            # Disable the select menu
            self.disabled = True
            await interaction.message.edit(view=self.view)

            await self.view.play_command.play_from_url(
                interaction=interaction, url=selected_video.embed_url
            )

        except Exception as e:
            log.error(f"Error in song selection: {e}")
            await interaction.response.send_message(
                f"Failed to play selected song: {str(e)}",
            )
