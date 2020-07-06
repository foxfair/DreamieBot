import asyncio
import json
import os
import time

import discord
from discord.ext import commands
from ext import auth_config
from ext import checks
from ext import sheet
from ext import utils

from dotenv import load_dotenv
load_dotenv()

LOG_CHANNEL = os.getenv('LOG_CHANNEL')

is_staff = checks.is_staff()


class Staff(commands.Cog):
    '''Staff commands to manage villager applications.'''

    def __init__(self, bot):
        self.bot = bot
        self._last_result = None
        self.sessions = set()

    @commands.command(hidden=True)
    async def send_logs(self, data):
        '''Send logs to a logging channel.'''
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(int(LOG_CHANNEL))
        await channel.send(data)

    @commands.command(name='list', aliases=['li'])
    @is_staff
    async def list(self, ctx, req_id=None):
        '''List all requests, or a single request by its ID.'''
        # Retrieve data_dict from the request log file.
        data_dict = utils.open_requestlog()
        found = ""
        for request_id, details in list(data_dict.items()):
            if not req_id or str(request_id) == req_id:
                # all requests.
                found += 'request_id: %s\n' % request_id
                found += utils.printadict(details)
                found += '\n'
        if found:
            time.sleep(1)
            pg_data = utils.paginate(found)
            embed = discord.Embed(title='List Requests')
            embed.color = utils.random_color()
            for message in pg_data:
                embed.description = ''.join(message)
                await ctx.send(embed=embed)

    @commands.command(name='review', aliases=['rev'],
                      usage=('<req_id> will approve a request by its ID.\n'
                             'To reject a request, use "!review <req_id> denied"'))
    @is_staff
    async def review(self, ctx, req_id, denied=None):
        '''Review a request. The result is either approved or denied.'''
        data_dict = utils.open_requestlog()
        user_id = 0
        staff = None
        found = False
        found_data = dict()
        for request_id, details in list(data_dict.items()):
            if int(request_id) == int(req_id):
                found = True
                staff = ctx.message.author.name
                user_id = int(details['user_id'])
                if str(denied) == 'denied':
                    # The message is sent back to a user.
                    message = ':disappointed_relieved: Your application was rejected'
                    message += ' after reviewed by the staff team. The request has been closed.\n'
                    message += '**NOTE: It is simply meant that you have less involved within '
                    message += 'the community of the server.**\nPlease talk to any active '
                    message += 'member in your perferred channels, and join all '
                    message += 'activities you would like to go. \nYou can apply again '
                    message += '**after one month** from now.'
                    # A server message for reference.
                    server_message = '%s denied a request: %s' % (staff, req_id)
                    await ctx.send(server_message)

                    details['status'] = utils.Status.CANCEL.name
                    # mark a last_modified timestring
                    tm = time.localtime(time.time())
                    timestring = time.strftime("%Y-%m-%d %I:%M:%S%p %Z", tm)
                    details['last_modified'] = timestring

                    # send to log channel
                    await self.send_logs(server_message)
                    # send a DM to note the user.
                    if user_id:
                        user = self.bot.get_user(user_id)
                        dm_chan = user.dm_channel or await user.create_dm()
                        await dm_chan.send(message)
                else:
                    message = 'Request **%s** is now approved by %s!'
                    await ctx.send(message % (req_id, staff))
                    details['status'] = utils.Status.PROCEED.name
                    # mark a last_modified timestring
                    tm = time.localtime(time.time())
                    timestring = time.strftime("%Y-%m-%d %I:%M:%S%p %Z", tm)
                    details['last_modified'] = timestring

                    # send to log channel
                    await self.send_logs('%s approved a request: %s' % (staff, req_id))
                    # send a DM to note the user.
                    if user_id:
                        user = self.bot.get_user(user_id)
                        dm_chan = user.dm_channel or await user.create_dm()
                        await dm_chan.send('Your request **%s** is approved by a staff(%s).' % (req_id, staff))
                        await dm_chan.send('Please use the **!status** command to check the latest status.')
                # Save changes to found_data
                found_data[request_id] = details
        if not found:
            message = 'Cannot find request **%s**' % req_id
            await ctx.send(message)
            # send to log channel
            await self.send_logs(message)
            return
	# Write changes back.
        utils.flush_requestlog(data_dict)
        sheet.update_data(found_data)

    @commands.command(name='found', aliases=['fnd'])
    @is_staff
    async def found(self, ctx, req_id):
        '''Indicates that you have found a requested villager.'''
        data_dict = utils.open_requestlog()
        user_id = 0
        staff = None
        dreamie = ''
        found_data = dict()
        for request_id, details in list(data_dict.items()):
            if str(request_id) == str(req_id):
                staff = ctx.message.author.name
                message = 'A villager of this request **%s** was found by %s!'
                await ctx.send(message % (req_id, staff))
                details['status'] = utils.Status.FOUND.name
                dreamie = details['villager']
                # only get the name
                dreamie = dreamie.split(',')[0]
                # mark a last_modified timestring
                tm = time.localtime(time.time())
                timestring = time.strftime("%Y-%m-%d %I:%M:%S%p %Z", tm)
                details['last_modified'] = timestring
                user_id = int(details['user_id'])
                found_data[request_id] = details

        utils.flush_requestlog(data_dict)
        sheet.update_data(found_data)

        # send to log channel
        await self.send_logs('%s found a requested villager: %s' % (staff, dreamie))
        # send a DM to note the user.
        if user_id:
            user = self.bot.get_user(user_id)
            dm_chan = user.dm_channel or await user.create_dm()
            message = '%s We found your dreamie! %s is now being fostered.\n'
            message += 'You will be contacted by *%s* to coordinate the following steps during '
            message += 'your selected timeslot. \n'
            message += 'Request Id: **%s**'
            await dm_chan.send(message % (user.mention, dreamie, staff, req_id))

    @commands.command(name='close', aliases=['cls'])
    @is_staff
    async def close(self, ctx, req_id):
        '''Close a request and pop some firework.'''
        data_dict = utils.open_requestlog()
        user_id = 0
        staff = None
        villager = None
        found_data = dict()
        for request_id, details in list(data_dict.items()):
            if str(request_id) == str(req_id):
                staff = ctx.message.author.name
                message = 'Congrats! Request **%s** is now closed by %s!'
                villager = details['villager'].split(',')[0]
                await ctx.send(message % (req_id, staff))
                details['status'] = utils.Status.CLOSED.name
                # mark a last_modified timestring
                tm = time.localtime(time.time())
                timestring = time.strftime("%Y-%m-%d %I:%M:%S%p %Z", tm)
                details['last_modified'] = timestring
                user_id = int(details['user_id'])
                found_data[request_id] = details

        utils.flush_requestlog(data_dict)
        sheet.update_data(found_data)

        # send to log channel
        await self.send_logs('%s closed a request: %s' % (staff, req_id))
        # send a DM to note the user.
        if user_id:
            user = self.bot.get_user(user_id)
            dm_chan = user.dm_channel or await user.create_dm()
            message = 'Congrats, %s! You have found your dreamie, %s. \nYour request **%s** is closed by a staff (%s).'
            await dm_chan.send(message % (user.mention, villager, req_id, staff))

    @commands.command(name='inspect', aliases=['isp'], hidden=True)
    async def inspect(self, ctx):
        '''Inspect a user information and report back.'''
        name = ctx.message.author.name
        user_id = ctx.message.author.id
        user_obj = self.bot.get_user(user_id)
        content = ctx.message.content
        channel_id = ctx.message.channel.id
        permission = ctx.message.channel.permissions_for(user_obj)
        message = '%s Here is your inspection data: ID=%s. Channel ID: %s. Permission: %s.'
        await ctx.send(message % (user_obj.mention, user_id, channel_id, permission))
        # send to log channel
        log_message = 'Inspected user: name=%s, ID=%s. Channel ID: %s. Permission: %s.'
        await self.send_logs(log_message % (name, user_id, channel_id, permission))


def setup(bot):
    bot.add_cog(Staff(bot))
    print('Staff module loaded.')
