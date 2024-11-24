import re

from discord import ButtonStyle, Interaction, ui


class DynamicButton(ui.DynamicItem[ui.Button], template=r"button:user:(?P<id>[0-9]+)"):
    def __init__(self, user_id: int) -> None:
        super().__init__(
            ui.Button(
                label="Do Thing",
                style=ButtonStyle.blurple,
                custom_id=f"button:user:{user_id}",
                emoji="\N{THUMBS UP SIGN}",
            )
        )
        self.user_id: int = user_id

    # This is called when the button is clicked and the custom_id matches the template.
    @classmethod
    async def from_custom_id(
        cls, interaction: Interaction, item: ui.Button, match: re.Match[str], /
    ):
        user_id = int(match["id"])
        return cls(user_id)

    async def interaction_check(self, interaction: Interaction) -> bool:
        # Only allow the user who created the button to interact with it.
        return interaction.user.id == self.user_id

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.send_message("This is your very own button!", ephemeral=True)
