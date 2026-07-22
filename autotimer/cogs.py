"""Discord bot cog that watches designated channels for timer pastes.

When a paste is detected the bot replies with a structure-type dropdown.
Picking a type creates the timer immediately; if nobody picks within
``AUTOTIMER_SELECT_TIMEOUT_SECONDS`` a fallback celery task creates it with
the default structure type (the duplicate guard makes the fallback a silent
no-op when a selection already created the timer).

The dropdown survives bot restarts: the view is persistent and the select
callback re-reads the original pasted message instead of relying on any
in-memory state.
"""

import discord
from discord.ext import commands

from allianceauth.services.hooks import get_extension_logger

from . import app_settings
from .parser import parse_message
from .tasks import create_timers_from_message

logger = get_extension_logger(__name__)

SELECT_CUSTOM_ID = "autotimer:structure_type"


class StructureTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=label, value=str(type_id))
            for label, type_id in app_settings.structure_type_choices()
        ]
        super().__init__(
            custom_id=SELECT_CUSTOM_ID,
            placeholder="Select the structure type\N{HORIZONTAL ELLIPSIS}",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        type_id = int(self.values[0])
        label = next(
            (
                label
                for label, choice_id in app_settings.structure_type_choices()
                if choice_id == type_id
            ),
            f"type {type_id}",
        )
        original = await self._fetch_original_message(interaction)
        if original is None or not parse_message(original.content):
            await interaction.response.edit_message(
                content=(
                    "\N{CROSS MARK} Could not find the original timer paste "
                    "(was it deleted?)"
                ),
                view=None,
            )
            return
        create_timers_from_message.delay(
            message_content=original.content,
            channel_id=interaction.channel.id,
            author_name=str(original.author.display_name),
            structure_type_id=type_id,
        )
        logger.info(
            "Structure type %s picked by %s for message %d",
            label,
            interaction.user,
            original.id,
        )
        await interaction.response.edit_message(
            content=(
                f"Creating timer as **{label}** "
                f"(picked by {interaction.user.display_name})\N{HORIZONTAL ELLIPSIS}"
            ),
            view=None,
        )

    @staticmethod
    async def _fetch_original_message(interaction: discord.Interaction):
        reference = interaction.message.reference if interaction.message else None
        if not reference or not reference.message_id:
            return None
        if reference.resolved and isinstance(reference.resolved, discord.Message):
            return reference.resolved
        try:
            return await interaction.channel.fetch_message(reference.message_id)
        except discord.HTTPException:
            return None


class StructureTypeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(StructureTypeSelect())


class AutoTimer(commands.Cog):
    """Creates Structure Timers from EVE client pastes."""

    def __init__(self, bot):
        self.bot = bot
        self._view_registered = False

    @commands.Cog.listener("on_ready")
    async def register_persistent_view(self):
        # Views can only be created once the event loop is running, and
        # on_ready can fire again on reconnects - register only once.
        if not self._view_registered:
            self.bot.add_view(StructureTypeView())
            self._view_registered = True
            logger.info("Registered persistent structure type view")

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

        if all(p.is_mercenary_den for p in parsed):
            # The paste format itself is unambiguous - no need to ask.
            create_timers_from_message.delay(
                message_content=message.content,
                channel_id=message.channel.id,
                author_name=str(message.author.display_name),
            )
            return

        timeout = app_settings.select_timeout_seconds()
        try:
            await message.reply(
                (
                    f"Found **{len(parsed)}** timer paste(s). What structure "
                    f"is this? (defaults in {timeout // 60} min if nobody picks)"
                ),
                view=StructureTypeView(),
                mention_author=False,
            )
        except Exception:
            logger.warning(
                "Could not send dropdown for message %d", message.id, exc_info=True
            )
        # Fallback: create with the default type after the timeout. If a
        # selection already created the timer, the duplicate guard makes
        # this a silent no-op.
        create_timers_from_message.apply_async(
            kwargs={
                "message_content": message.content,
                "channel_id": message.channel.id,
                "author_name": str(message.author.display_name),
                "structure_type_id": None,
                "quiet": True,
            },
            countdown=timeout,
        )


def setup(bot):
    bot.add_cog(AutoTimer(bot))
