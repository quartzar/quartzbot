"""Database module for handling database connections"""

import logging

from tortoise import Tortoise

log = logging.getLogger(__name__)


class Database:
    def __init__(self, bot):
        self.bot = bot
        self.db_url = "sqlite:///app/data/db.sqlite3"

    async def init(self):
        """Initialise database connection"""
        log.info("Initialising database connection...")
        try:
            await Tortoise.init(
                db_url=self.db_url,
                modules={"models": ["src.models"]},
            )
        except Exception as e:
            log.exception("Failed to initialise database connection: %s", str(e))
            raise
        log.info("Database connection initialised")

        log.info("Generating database schemas...")
        try:
            await Tortoise.generate_schemas(safe=True)
        except Exception as e:
            log.exception("Failed to generate schemas: %s", str(e))
            raise
        log.info("Database schemas generated")

    async def close(self):
        """Close database connections"""
        await Tortoise.close_connections()

    async def describe_all_models(self):
        """Describe all models in the database"""
        import inspect

        import src.models

        models = inspect.getmembers(src.models, inspect.isclass)
        return "\n".join([f"{name}: {model}" for name, model in models])
