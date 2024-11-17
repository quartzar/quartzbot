import importlib
import logging
from pathlib import Path

from discord import Client, Object
from watchfiles import awatch

log = logging.getLogger(__name__)


class CogReloader:
    def __init__(self, bot: Client, cog_path: str = "src/cogs"):
        self.bot = bot
        self.cog_path = Path(cog_path)
        self.watching = False
        self.cogs: dict[str, object] = {}
        self.registered_commands: dict[str, set[str]] = {}

    async def load_cogs(self) -> None:
        """Load all cogs initially"""
        try:
            # Clear all commands first
            self.bot.tree.clear_commands(guild=None)
            if self.bot.guild_id:
                self.bot.tree.clear_commands(guild=Object(id=self.bot.guild_id))

            # Get all cog directories
            cog_dirs = [
                d for d in self.cog_path.iterdir()
                if d.is_dir() and not d.name.startswith("__")
            ]

            # Load each cog
            for cog_dir in cog_dirs:
                await self.load_cog(cog_dir.name)

            # Copy global commands to guild if needed
            if self.bot.guild_id:
                self.bot.tree.copy_global_to(guild=Object(id=self.bot.guild_id))
                await self.bot.tree.sync(guild=Object(id=self.bot.guild_id))
            else:
                await self.bot.tree.sync()

            log.info("[green]All cogs loaded and commands synced[/]")

        except Exception as e:
            log.error(f"[red]Failed to load cogs: {str(e)}[/]")
            raise

    async def load_cog(self, cog_name: str) -> None:
        """Load a single cog"""
        try:
            # Import and reload the module
            module = importlib.import_module(f"src.cogs.{cog_name}.cog")
            module = importlib.reload(module)

            # Get the cog class
            cog_class = getattr(module, f"{cog_name.title()}Cog")

            # Remove old commands if cog was previously loaded
            if cog_name in self.registered_commands:
                for cmd_name in self.registered_commands[cog_name]:
                    self.bot.tree.remove_command(cmd_name)
                self.registered_commands[cog_name].clear()

            # Create new cog instance and store commands
            cog = cog_class(self.bot)
            self.registered_commands[cog_name] = {
                cmd.name for cmd in cog.__cog_app_commands__
            }

            # Add new commands
            for cmd in cog.__cog_app_commands__:
                self.bot.tree.add_command(cmd)

            # Store cog reference
            self.cogs[cog_name] = cog
            log.info(f"[green]Loaded cog: {cog_name}[/]")

        except Exception as e:
            log.error(f"[red]Failed to load cog {cog_name}: {str(e)}[/]")
            raise

    async def start_watching(self) -> None:
        """Start watching for file changes"""
        if self.watching:
            return

        self.watching = True
        log.info(f"[yellow]Starting file watcher for {self.cog_path}[/]")

        async for changes in awatch(self.cog_path):
            for change_type, file_path in changes:
                path = Path(file_path)
                if path.suffix == ".py" and not path.name.startswith("__"):
                    cog_name = path.parent.name
                    if cog_name in self.cogs:
                        log.info(f"[yellow]Detected changes in {cog_name}, reloading...[/]")
                        try:
                            await self.load_cog(cog_name)

                            # Resync commands after reload
                            if self.bot.guild_id:
                                self.bot.tree.copy_global_to(guild=Object(id=self.bot.guild_id))
                                await self.bot.tree.sync(guild=Object(id=self.bot.guild_id))
                            else:
                                await self.bot.tree.sync()

                            log.info(f"[green]Successfully reloaded {cog_name}[/]")
                        except Exception as e:
                            log.error(f"[red]Failed to reload {cog_name}: {str(e)}[/]")