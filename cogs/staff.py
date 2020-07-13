import asyncio
import json
import os
import time

import discord
from discord.ext import commands
from cogs import request
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
        # TODO: remove these two after confirm they are not used.
        self._last_result = None
        self.sessions = set()
        self.is_bot_locked = False
        
    @commands.command(hidden=True)
    async def send_logs(self, data):
        '''Send logs to a logging channel.'''
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(int(LOG_CHANNEL))
        await channel.send(data)

    @commands.command(name='list', aliases=['li'])
    @is_staff
    async def list(self, ctx, req_id=None):
        '''List all applications, or a single one by its ID.'''
        # Retrieve data_dict from the request log file.
        data_dict = utils.open_requestlog()
        found = ""
        for request_id, details in list(data_dict.items()):
            if not req_id or str(request_id) == req_id:
                # all requests.
                found += 'application_id: %s\n' % request_id
                found += utils.printadict(details)
                found += '\n'
        if found:
            time.sleep(1)
            pg_data = utils.paginate(found)
            embed = discord.Embed(title='List Applications')
            embed.color = utils.random_color()
            for message in pg_data:
                embed.description = ''.join(message)
                await ctx.send(embed=embed)

    @commands.command(name='review', aliases=['rev'],
                      usage=('<req_id> will approve an application by its ID.\n'
                             'To reject one, use "!review <req_id> denied"'))
    @is_staff
    async def review(self, ctx, req_id, denied=None):
        '''Review an application. The result is either approved or denied.'''
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
                    message = ':disappointed_relieved: Thank you for submitting an application for '
                    message += 'your dream villager! Unfortunately, your application has been '
                    message += 'rejected after being reviewed by the Beyond Stalks Villager Adoption Team.' 
                    message += '\n\nThe reason for your application\'s rejection is inactivity within '
                    message += 'the server community. Our adoption program is designed to be a reward '
                    message += 'for consistently active and positive contributers to the server. '
                    message += 'Please strive to meet these conditions and we will look forward to '
                    message += 'a follow-up application from you in due time. You may submit a new '
                    message += 'application in **2 weeks**.\n'
                    message += '\nYour application has been closed.\n\n'
                    message += 'Thanks!\nThe Villager Adoption Team'
                    # A server message for reference.
                    server_message = '%s denied an application: %s' % (staff, req_id)
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
                    message = 'Application **%s** is now approved by %s!'
                    await ctx.send(message % (req_id, staff))
                    details['status'] = utils.Status.PROCESSING.name
                    # mark a last_modified timestring
                    tm = time.localtime(time.time())
                    timestring = time.strftime("%Y-%m-%d %I:%M:%S%p %Z", tm)
                    details['last_modified'] = timestring

                    # send to log channel
                    await self.send_logs('%s approved an application: %s' % (staff, req_id))
                    # send a DM to note the user.
                    if user_id:
                        user = self.bot.get_user(user_id)
                        dm_chan = user.dm_channel or await user.create_dm()
                        await dm_chan.send('Your application **%s** is approved by a staff (_%s_).' % (req_id, staff))
                        await dm_chan.send('Please use the **!status** command to check current status.')
                # Save changes to found_data
                found_data[request_id] = details
        if not found:
            message = 'Cannot find application **%s**' % req_id
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
                message = 'A villager of this application **%s** was found by %s!'
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
        '''Close an application and pop some firework.'''
        data_dict = utils.open_requestlog()
        user_id = 0
        staff = None
        villager = None
        found_data = dict()
        for request_id, details in list(data_dict.items()):
            if str(request_id) == str(req_id):
                staff = ctx.message.author.name
                message = 'Congrats! Application **%s** is now closed by %s!'
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
        await self.send_logs('%s closed an application: %s' % (staff, req_id))
        # send a DM to note the user.
        if user_id:
            user = self.bot.get_user(user_id)
            dm_chan = user.dm_channel or await user.create_dm()
            message = 'Congrats, %s! You have found your dreamie, %s. \n'
            message += 'Your application **%s** is closed by a staff (%s).'
            await dm_chan.send(message % (user.mention, villager, req_id, staff))

    @commands.command(name='lock', aliases=['loc'])
    @is_staff
    async def lock(self, ctx):
        '''Lock the bot and reject any new application. Use it again to unlock.'''
        def get_state_text(state):
            "Wrapper function to get lock/unlock texts based on states."
            return 'lock' if state else 'unlock'
            
        staff = ctx.message.author.name

        # Setup a Flow controller.
        flow = request.Flow(self.bot, ctx)
        # debug
        # print??

        # Flip the bot status.
        current_state_text = get_state_text(self.is_bot_locked)
        next_state_text = get_state_text(not self.is_bot_locked)
        are_you_sure = await ctx.send(f":question: DreamieBot is currently {current_state_text}ed.\n"
                                      f"Please react to change state to **{next_state_text}** it: ")
        reaction = await flow.get_yes_no_reaction_confirm(are_you_sure, 200)
        if reaction is None:
            return
        if not reaction:
            return await ctx.send("Aborted locking da bot.")
        elif reaction:
            self.is_bot_locked = not self.is_bot_locked
            if self.is_bot_locked:
                # Change the bot's presence to dnd. use this status to indicate
                # that "do not distrub" it and reject all newer applications.
                lock_activity = discord.Game(name='Locked All Applications', state='LOCKED')
                new_status = discord.Status.dnd
                await self.bot.change_presence(status=new_status, activity=lock_activity)
                await ctx.send(f"You have locked the bot, use **!lock** command again to unlock it.")
            else:
                # Manually revert back to the original status=online.
                await self.bot.change_presence(activity=discord.Game(f"Fostering Dreamies"), afk=True)
                await ctx.send(f"You have unlocked the bot and it is back in business.")
        # send to log channel
        await self.send_logs('%s has **%sed** DreamieBot.' % (staff, next_state_text))

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
