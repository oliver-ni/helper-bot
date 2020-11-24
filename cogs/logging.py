import logging
from datetime import datetime

from discord.ext import commands

formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")


class Logging(commands.Cog):
    """For logging."""

    def __init__(self, bot):
        self.bot = bot

        self.log = logging.getLogger(f"Support")
        handler = logging.FileHandler(f"logs/support.log")
        handler.setFormatter(formatter)
        self.log.handlers = [handler]

        dlog = logging.getLogger("discord")
        dhandler = logging.FileHandler(f"logs/discord.log")
        dhandler.setFormatter(formatter)
        dlog.handlers = [dhandler]

        self.log.setLevel(logging.DEBUG)
        dlog.setLevel(logging.INFO)

    async def resync_guild(self, guild):
        await self.bot.mongo.db.guild.update_one(
            {"_id": guild.id},
            {
                "$set": {
                    "name": guild.name,
                    "icon": str(guild.icon_url),
                    "channels": [
                        {"id": channel.id, "type": channel.type, "name": channel.name}
                        for channel in guild.channels
                    ],
                }
            },
            upsert=True,
        )

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        await self.resync_guild(channel.guild)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        await self.resync_guild(channel.guild)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        await self.resync_guild(after.guild)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        await self.resync_guild(after.guild)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.resync_guild(guild)

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        await self.resync_guild(after)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None:
            return
        time = int(message.created_at.timestamp())
        await self.bot.mongo.db.message.insert_one(
            {
                "_id": message.id,
                "user_id": message.author.id,
                "channel_id": message.channel.id,
                "guild_id": message.guild.id,
                "history": {str(time): message.content},
                "attachments": [
                    {"id": attachment.id, "filename": attachment.filename}
                    for attachment in message.attachments
                ],
                "deleted_at": None,
            }
        )

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        if "content" not in payload.data:
            return
        time = int(datetime.utcnow().timestamp())
        await self.bot.mongo.db.message.update_one(
            {"_id": payload.message_id},
            {"$set": {f"history.{time}": payload.data["content"]}},
        )

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        if payload.cached_message is not None:
            for attachment in payload.cached_message.attachments:
                fn = f"attachments/{attachment.id}_{attachment.filename}"
                self.bot.loop.create_task(attachment.save(fn, use_cached=True))
        await self.bot.mongo.db.message.update_one(
            {"_id": payload.message_id},
            {"$set": {"deleted_at": datetime.utcnow()}},
        )

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        await self.bot.mongo.db.message.update_many(
            {"_id": {"$in": list(payload.message_ids)}},
            {"$set": {"deleted_at": datetime.utcnow()}},
        )


def setup(bot):
    bot.add_cog(Logging(bot))
