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

    # mainly from https://repl.it/talk/learn/Discordpy-Rewrite-Tutorial-using-commands-extension/10690
"""    @commands.command(name='help',
                      description='This help command!',
                      aliases=['h', 'commands', 'command'],
                      usage='cog')
    async def help_command(self, ctx, cog='all'):
        '''A customized help command.'''
        # The third parameter comes into play when
        # only one word argument has to be passed by the user

        # Prepare the embed

        # color_list = [c for c in colors.values()]

        help_embed = discord.Embed(
            title='Help',
            color=utils.random_color()
        )
        help_embed.set_thumbnail(url=self.bot.user.avatar_url)
        help_embed.set_footer(text=f'Requested by {ctx.author.name}',
            icon_url=self.bot.user.avatar_url)

        # Get a list of all cogs
        cogs = [c for c in self.bot.cogs.keys()]
        # If cog is not specified by the user, we list all cogs and commands

        if cog == 'all':

            for cog in cogs:
                # Get a list of all commands under each cog

                cog_commands = self.bot.get_cog(cog).get_commands()
                staff_commands = self.bot.get_cog('Staff').get_commands()
                user_commands = self.bot.get_cog(cogs[ cogs.index('User') ]).get_commands()

                commands_list = ''

                #for comm in cog_commands:
                #    commands_list += f'**{comm.name}** - *{comm.description}*'

                for comm in user_commands:
                    commands_list += f'**{comm.name}** - *{comm.description}*\n'
                if is_staff:
                    for comm in staff_commands:
                        commands_list += f'**{comm.name}** - *{comm.description}*\n'
                # Add the cog's details to the embed.
                help_embed.add_field(
                    name=cog,
                    value=commands_list,
                    inline=False
                ).add_field(
                    name='\u200b', value='\u200b', inline=False
                )

                # Also added a blank field '\u200b' is a whitespace character.
            pass
        else:
            # If the cog was specified

            lower_cogs = [c.lower() for c in cogs]

            if cog.lower() == 'staff' and not is_staff:
                await ctx.send('You are not allowed to use staff commands.')
                return

            # If the cog actually exists.
            if cog.lower() in lower_cogs:

                # Get a list of all commands in the specified cog
                commands_list = self.bot.get_cog(cogs[ lower_cogs.index(cog.lower()) ]).get_commands()
                help_text=''

                # Add details of each command to the help text
                # Command Name
                # Description
                # [Aliases]
                #
                # Format
                if cog.lower() == 'staff' and not is_staff:
                    raise commands.DisabledCommand('You are not allowed to use staff commands.')

                for command in commands_list:
                    help_text += f'```{command.name}```\n' \
                        f'**{command.description}**\n\n'

                    # Also add aliases, if there are any
                    if len(command.aliases) > 0:
                        help_text += f'**Aliases :** `{"`, `".join(command.aliases)}`\n\n\n'
                    else:
                        # Add a newline character to keep it pretty
                        # That IS the whole purpose of custom help
                        help_text += '\n'

                    # Finally the format
                    help_text += f'Format: `@{self.bot.user.name}#{self.bot.user.discriminator}' \
                        f' {command.name} {command.usage if command.usage is not None else ""}`\n\n\n\n'

                help_embed.description = help_text
            else:
                # Notify the user of invalid cog and finish the command
                await ctx.send('Invalid cog specified.\nUse `help` command to list all cogs.')
                return

        await ctx.send(embed=help_embed)

        return    
"""




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

    async def get_yes_no_reaction_confirm(self, message: discord.Message, timeout: int) -> typing.Optional[bool]:
        """Adds the :white_check_mark: and :x: emoji to the message and returns the reaction and user if either
           reaction has been added by the original user.
           Returns None if the user did nothing."""

        yes_emoji = self.yes_emoji
        no_emoji = self.no_emoji

        await message.add_reaction(yes_emoji)
        await message.add_reaction(no_emoji)

        try:
            reaction, user = await self.ctx.bot.wait_for('reaction_add',
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


    async def get_timeslot_reaction_confirm(self, message: discord.Message, timeout: int) -> typing.Optional[bool]:
        """Adds the numbers 1-6 emoji to the message and returns the reaction and user if either
           reaction has been added by the original user.
           Returns None if the user did nothing."""

        slot1_emoji = "\U00002728"
        slot2_emoji = "\U00002733"
        slot3_emoji = "\U00002764"
        slot4_emoji = "\U0001F680"
        slot5_emoji = "\U0001F684"
        slot6_emoji = "\U0001F68F"

        for emoji in (slot1_emoji, slot2_emoji, slot3_emoji, slot4_emoji,
                      slot5_emoji, slot6_emoji):
            await message.add_reaction(emoji)

        try:
            reaction, user = await self.ctx.bot.wait_for('reaction_add',
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
