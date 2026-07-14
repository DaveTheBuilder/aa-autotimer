"""Discord bot cog that watches designated channels for timer pastes."""

from discord.ext import commands

from allianceauth.services.hooks import get_extension_logger

from . import app_settings
from .parser import parse_message
from .tasks import create_timers_from_message

logger = get_extension_logger(__name__)


class AutoTimer(commands.Cog):
    """Creates Structure Timers from EVE client pastes."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.channel.id not in app_settings.channel_ids():
            return
        parsed = parse_message(message.content)
        if not parsed:
            return
        logger.info(
            "Found %d timer paste(s) in message %d from %s",
            len(parsed),
            message.id,
            message.author,
        )
        try:
            await message.add_reaction("\N{HOURGLASS WITH FLOWING SAND}")
        except Exception:
            logger.warning(
                "Could not react to message %d", message.id, exc_info=True
            )
        create_timers_from_message.delay(
            message_content=message.content,
            channel_id=message.channel.id,
            author_name=str(message.author.display_name),
        )


def setup(bot):
    bot.add_cog(AutoTimer(bot))
