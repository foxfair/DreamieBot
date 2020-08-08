'''Background tasks module.'''
import datetime
import os
import time

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from ext import auth_config
from ext import sheet
from ext import utils

load_dotenv()

TIME_FORMAT = os.getenv('TIME_FORMAT')
# When an application is found/ready, we allow 72 hours until it is finished.
COUNTDOWN_HOURS = int(os.getenv('COUNTDOWN_HOURS'))

class Background(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_status = dict()
        self.monitoring.start()
        # Use loop_counter to fire a countdown monitoring when
        # monitoring tasks are running at the same time.
        self.loop_counter = -1

    def cog_unload(self):
        self.monitoring.cancel()

    @tasks.loop(minutes=15)
    async def monitoring(self):
        '''Monitoring applications and report it back to #adoption-team's channel.'''
        # For testing, lets just spam foxfair.
        user = self.bot.get_user(self.bot.owner_id)
        dm_chan = user.dm_channel or await user.create_dm()
        # Send message to #villager-adption-team channel.
        team_chan = self.bot.get_channel(auth_config.SEND_MSG_CHANNELS[1])
        staff_cog = self.bot.get_cog('Staff')
        for status in ('pending', 'found', 'approved', 'ready', 'processing'):
            report = await staff_cog.search(None, status, 'background')
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
                    await team_chan.send(embed=embed)
        # To guarantee the first task will monitor this 'countdown' task.
        self.loop_counter += 1
        if (self.loop_counter % 4) == 0:
            status = 'ready'
            report = await staff_cog.search(None, status, 'countdown')
            if report:
                for req_id, details in report.items():
                    current = datetime.datetime.utcnow()
                    for exp_min in [360, 180, 60]:
                        app_user = self.bot.get_user(details['user_id'])
                        # Prepare to send a DM to remind the applicant
                        reminder_chan = app_user.dm_channel or await app_user.create_dm()
                        then_ts = time.strptime(details['last_modified'], TIME_FORMAT)
                        then_dt = datetime.datetime.fromtimestamp(time.mktime(then_ts))
                        deadline = datetime.timedelta(hours=COUNTDOWN_HOURS)
                        reminder_period = datetime.timedelta(minutes=exp_min)
                        time_left = then_dt + deadline - current
                        if (then_dt + deadline) <= current:
                            user_msg = ('{} Your application ID: {}, was '
                                        'expired after 72 hours, and it was '
                                        'closed automatically.'.format(
                                            app_user.mention, req_id))
                            # Expired; closed by DreamieBot.
                            data_dict = utils.open_requestlog()
                            found_data = dict()
                            for request_id, details in data_dict.items():
                                if request_id == req_id:
                                    details['status'] = utils.Status.CLOSED.name
                                    # mark a last_modified timestring
                                    tm = time.localtime(time.time())
                                    timestring = time.strftime(TIME_FORMAT, tm)
                                    details['last_modified'] = timestring
                                    details['staff'] = 'DreamieBot#1424'
                                    found_data[request_id] = details
                            utils.flush_requestlog(data_dict)
                            server_msg = ('DreamitBot closed an expired '
                                          'application {} at {}'.format(
                                                req_id, timestring))
                            await reminder_chan.send(user_msg)
                            await staff_cog.send_logs(server_msg)
                            time.sleep(1)
                            await team_chan.send(embed=embed)
                            await sheet.update_data(found_data)
                            msg = ('DreamieBot archived the row of {} in the '
                                   'sheet.' % req_id)
                            await staff_cog.send_logs(msg)
                            return await sheet.archive_column(req_id)
                        elif time_left <= reminder_period:
                            # remove microsecond, users dont care.
                            time_left = utils.chop_microseconds(time_left)
                            message = ('{} Your application has been ready but '
                                       'the timer is approaching to the {} '
                                       'hours limit.\nRemaining time is {}.\n'
                                       'Please use `~status` to see the details'
                                       'and contact your staff, {}, to complete'
                                       'your application ASAP.'.format(
                                            app_user.mention, COUNTDOWN_HOURS,
                                            time_left, details['staff']))
                            self.key = 'reminder-{}-{}'.format(exp_min, user.name)
                            # Put into self.last_status and avoid spammy messages.
                            if self.key not in self.last_status:
                                self.last_status[self.key] = req_id
                                await reminder_chan.send(message)
                                # send logs to log channel
                                log_msg = 'Send a reminder to {}: {}'.format(
                                            app_user.mention, self.key)
                                await staff_cog.send_logs(log_msg)
                        else:
                            # debug
                            # print('current time: %s' % current)
                            # print('timer left: %s' % (then_dt+deadline-current))
                            pass


    @monitoring.before_loop
    async def before_monitoring(self):
        await self.bot.wait_until_ready()



def setup(bot):
    bot.add_cog(Background(bot))
    print('Background module loaded.')
