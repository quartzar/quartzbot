"""Tortoise ORM models"""

from tortoise import fields
from tortoise.models import Model


class Guild(Model):
    id = fields.BigIntField(primary_key=True)
    name = fields.CharField(max_length=100)
    created_at = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        return "Guild: %(name)s with ID: %(id)d was created at: %(created_at)s" % {
            "name": self.name,
            "id": self.id,
            "created_at": self.created_at,
        }


class Channel(Model):
    id = fields.BigIntField(primary_key=True)
    name = fields.CharField(max_length=100)
    guild = fields.ForeignKeyField(
        "models.Guild", related_name="channels", on_delete=fields.CASCADE
    )
    created_at = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        return "Channel: %(name)s with ID: %(id)d was created at: %(created_at)s" % {
            "name": self.name,
            "id": self.id,
            "created_at": self.created_at,
        }


class PersistentMessage(Model):
    message_id = fields.BigIntField()
    guild = fields.ForeignKeyField(
        "models.Guild", related_name="persistent_message", on_delete=fields.CASCADE
    )
    channel = fields.ForeignKeyField(
        "models.Channel", related_name="persistent_message", on_delete=fields.CASCADE
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    last_updated = fields.DatetimeField(auto_now=True)

    class Meta:
        unique_together = ("guild", "channel")  # Ensure only one persistent message per channel

    def __str__(self):
        return (
            "Persistent message for guild: %(guild)s in channel: %(channel)s with message ID: %(message)d"
            % {
                "guild": self.guild.name,
                "channel": self.channel.name,
                "message": self.message_id,
            }
        )
