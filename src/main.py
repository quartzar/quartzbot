import asyncio
import logging
import os
import signal

from rich.console import Console
from rich.logging import RichHandler

from src.activities import Activities
from src.bot import QuartzBot

rich_handler = RichHandler(
    console=Console(width=120),
    markup=True,
    rich_tracebacks=True,
    enable_link_path=False,
    tracebacks_show_locals=True,
)

logging.basicConfig(level="INFO", format="%(message)s", datefmt="[%X]", handlers=[rich_handler])

log = logging.getLogger("rich")


async def main():
    bot = QuartzBot()
    # Set up signal handlers
    loop = asyncio.get_running_loop()
    signals = (signal.SIGTERM, signal.SIGINT)
    for sig in signals:
        loop.add_signal_handler(
            sig, lambda captured_sig=sig: asyncio.create_task(shutdown(captured_sig, loop, bot))
        )

    # Get token from environment
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("No Discord token found. Set DISCORD_TOKEN environment variable.")

    try:
        async with bot:
            await bot.start(token)
    except KeyboardInterrupt:
        log.info("Received keyboard interrupt")
    except asyncio.CancelledError:
        # This is expected during shutdown, we can safely ignore it
        log.info("[bold bright_green]Shutdown completed successfully![/]")
    except Exception as e:
        log.exception("Unexpected error during shutdown: %s", e)


async def shutdown(signal, loop, bot):
    """Cleanup tasks tied to the service's shutdown."""
    log.info(f"Received exit signal {signal.name}...")

    # Do cleanup before cancelling tasks
    if not bot.is_closed():
        try:
            # Set shutdown status and cleanup
            await bot.change_presence(**Activities.shutdown())

            # Stop and disconnect voice clients
            for voice_client in bot.voice_clients:
                if voice_client.is_playing():
                    voice_client.stop()
                await voice_client.disconnect(force=True)

            # Get music cog and cleanup temp files
            music_cog = bot.reloader.cogs.get("MusicCog")
            if music_cog and hasattr(music_cog, "cache"):
                temp_dir = music_cog.cache.temp_dir
                if os.path.exists(temp_dir):
                    for temp_file in os.listdir(temp_dir):
                        try:
                            os.unlink(os.path.join(temp_dir, temp_file))
                        except Exception as e:
                            log.error(f"Failed to cleanup temp file: {e}")

            # Wait briefly for cleanup
            await asyncio.sleep(1)

            # Close database connection
            await bot.db.close()

            # Close bot connection
            await bot.close()

        except Exception as e:
            log.error(f"Error during cleanup: {e}")

    # Then handle task cancellation
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]

    log.info(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)

    loop.stop()


if __name__ == "__main__":
    asyncio.run(main())
