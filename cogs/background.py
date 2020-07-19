'''Background tasks module.'''

import discord
from discord.ext import commands, tasks

from ext import auth_config
from ext import utils


class Background(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_status = dict()
        self.monitoring.start()

    def cog_unload(self):
        self.monitoring.cancel()

    @tasks.loop(minutes=15)
    async def monitoring(self):
        '''Monitoring applications and report it back to #adoption-team's channel.'''
        # For testing, lets just spam foxfair.
        user = self.bot.get_user(self.bot.owner_id)
        dm_chan = user.dm_channel or await user.create_dm()
        # Send message to #bot-logs channel.
        # chan = self.bot.get_channel(auth_config.SEND_MSG_CHANNELS[0])
        staff = self.bot.get_cog('Staff')
        for status in ('pending', 'found', 'approved', 'ready', 'processing'):
            report = await staff.search(None, status, 'background')
            title = '_%s_ Application' % status.capitalize()
            if len(report) > 1:
                title += 's: *%d*' % len(report)
            else:
                title += ': *%d*' % len(report)
            if report:
                embed = discord.Embed(title=title)
                embed.color = utils.random_color()
                for k, v in report.items():
                    embed.add_field(name=k, value=v, inline=True)
                # Save to self.last_status, and only report different/new info.
                # "if status not in self.last_status" means this is a new status.
                # "if report != self.last_status[status]" means data of this status
                # has changed.
                if status not in self.last_status or report != self.last_status[
                        status]:
                    self.last_status[status] = report
                    await dm_chan.send(embed=embed)
                    # await chan.send(embed=embed)

    @monitoring.before_loop
    async def before_monitoring(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=60.0)
    async def countdown(self):
        '''Monitoring user's ready case, and remind them when the time remains 6,3 and 1 hour.'''
        staff = self.bot.get_cog('Staff')
        report = await staff.search(None, 'ready', 'background')


def setup(bot):
    bot.add_cog(Background(bot))
    print('Background module loaded.')
