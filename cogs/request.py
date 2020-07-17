'''This module serves as a generic library.'''

import typing

import discord
from discord.ext import commands
from ext import checks
from ext import utils

is_staff = checks.is_staff()


class Request(commands.Cog):
    '''Generic class for request.'''
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None
        self.sessions = set()


# from https://github.com/jonasbohmann/democraciv-discord-bot/
class Flow:
    """The Flow class helps with user input that require the bot to wait for replies or reactions."""
    yes_emoji = "\U00002705"
    no_emoji = "\U0000274c"

    def __init__(self, bot, ctx):
        self.bot = bot
        self.ctx = ctx

    def wait_for_reaction_check(self, ctx, original_message: discord.Message):
        """Wrapper function for a client.wait_for('reaction_add') check"""
        def check(reaction, user):
            return user == ctx.author and reaction.message.id == original_message.id

        return check

    async def get_yes_no_reaction_confirm(
            self, message: discord.Message,
            timeout: int) -> typing.Optional[bool]:
        """Adds the :white_check_mark: and :x: emoji to the message and returns the reaction and user if either
           reaction has been added by the original user.
           Returns None if the user did nothing."""

        yes_emoji = self.yes_emoji
        no_emoji = self.no_emoji

        await message.add_reaction(yes_emoji)
        await message.add_reaction(no_emoji)

        try:
            reaction, user = await self.ctx.bot.wait_for(
                'reaction_add',
                check=self.wait_for_reaction_check(self.ctx, message),
                timeout=timeout)
        except asyncio.TimeoutError:
            await self.ctx.send(":zzz: You took too long to react.")
            return None

        else:
            if reaction is None:
                return None

            if str(reaction.emoji) == yes_emoji:
                return True

            elif str(reaction.emoji) == no_emoji:
                return False

    async def get_timeslot_reaction_confirm(
            self, message: discord.Message,
            timeout: int) -> typing.Optional[bool]:
        """Adds the numbers 1-6 emoji to the message and returns the reaction and user if either
           reaction has been added by the original user.
           Returns None if the user did nothing."""

        slot1_emoji = "\U00002728"
        slot2_emoji = "\U00002733"
        slot3_emoji = "\U00002764"
        slot4_emoji = "\U0001F680"
        slot5_emoji = "\U0001F319"
        slot6_emoji = "\U0001F314"

        for emoji in (slot1_emoji, slot2_emoji, slot3_emoji, slot4_emoji,
                      slot5_emoji, slot6_emoji):
            await message.add_reaction(emoji)

        try:
            reaction, user = await self.ctx.bot.wait_for(
                'reaction_add',
                check=self.wait_for_reaction_check(self.ctx, message),
                timeout=timeout)
        except asyncio.TimeoutError:
            await self.ctx.send(":zzz: You took too long to react.")
            return None

        else:
            if reaction is None:
                return None

            if str(reaction.emoji) == slot1_emoji:
                return 1
            elif str(reaction.emoji) == slot2_emoji:
                return 2
            elif str(reaction.emoji) == slot3_emoji:
                return 3
            elif str(reaction.emoji) == slot4_emoji:
                return 4
            elif str(reaction.emoji) == slot5_emoji:
                return 5
            elif str(reaction.emoji) == slot6_emoji:
                return 6


def setup(bot):
    bot.add_cog(Request(bot))
    print('Request module loaded.')
