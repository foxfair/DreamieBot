import asyncio
import json
import os
import re
import time
import urllib

import discord
from discord.ext import commands
from dotenv import load_dotenv

from cogs import request
from ext import checks
from ext import utils

load_dotenv()

RECORD_FILE = os.getenv('RECORD_FILE')
LOG_CHANNEL = os.getenv('LOG_CHANNEL')


class User(commands.Cog):
    '''User commands to maintain a villager application.'''

    def __init__(self, bot):
        self.bot = bot
        self._last_result = None
        self.sessions = set()

    @commands.command(hidden=True)
    async def send_logs_user(self, data):
        '''Send logs to a logging channel.'''
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(int(LOG_CHANNEL))
        await channel.send(data)

    @commands.command(name='request', aliases=['req'],
                      usage='<villager name>, i.e: !request Raymond')
    async def request(self, ctx, villager=None):
        '''Request a villager and get a <request ID> in return.'''
        
        # Setup a Flow controller.
        flow = request.Flow(self.bot, ctx)

        if not villager:
            text = 'Greetings! Which villager would you like to request?'
            em = utils.get_embed('gray', text)
            await ctx.channel.send(embed=em)
            return

        # Form a villager link
        villager_link = 'https://villagerdb.com/villager/{}'.format(villager.lower())
        villager = villager.capitalize()
        # Validate the villager's name before everything.
        result = checks.validate_name(villager)
        if result:
            await ctx.send(result)
            return
        villager_data = "{}, {}".format(villager, villager_link)

        request_id = ctx.message.id
        name = ctx.message.author.name
        
        message = checks.precheck(name, villager)
        if message:
            em = utils.get_embed('red', message, title='Precheck Failed')
            await ctx.channel.send(embed=em)
            # only for direct message.
            # Note that use ctx.send, not ctx.channel.send!
            # await ctx.send(message)
            return

        tm = time.localtime(time.time())
        timestring = time.strftime("%Y-%m-%d %I:%M:%S%p %Z", tm)
        # init data and data_dict
        data = ""
        data_dict = dict()
        data = u"Request_Id: **{}**\n".format(request_id)
        details = dict()
        data += u"Name: {}\n".format(name)
        details['name'] = name
        details['user_id'] = ctx.message.author.id
        data += 'Villager: {}\n'.format(villager_data)
        details['villager'] = villager_data
        data += u"CreatedTime: {}\n".format(timestring)
        details['created_time'] = timestring

        em = utils.get_embed('gray', 'Your Request Details:')
        await ctx.channel.send(embed=em)
        await ctx.send(utils.printadict(details, hide_self=True))
        time.sleep(1)
        # Flow control.
        tt_or_not = await ctx.send(f":information_source: Are you willing to do Time Travel in order to "
                                   f"make the process quicker?")
        tt_reaction = await flow.get_yes_no_reaction_confirm(tt_or_not, 200)
        if tt_reaction is None:
            return
        if not tt_reaction:
            details['can_time_travel'] = False
        else:
            details['can_time_travel'] = True

        are_you_sure = await ctx.send(f":question: Please confirm YES/NO to add a new "
                                      f"request of finding your dreamie **%s**" % villager)

        reaction = await flow.get_yes_no_reaction_confirm(are_you_sure, 200)
        if reaction is None:
            return
        if not reaction:
            return await ctx.send("Aborted your request.")
        elif reaction:
            user_obj = self.bot.get_user(ctx.message.author.id)
            await ctx.send("This request has been logged for review.")
            await ctx.send("%s Please take a note of your Request ID: **%s**" % (user_obj.mention, request_id))

            # Add a default status.
            data += u"Status: {}".format(utils.Status.PENDING.name)
            details['status'] = utils.Status.PENDING.name

            # data_dict is keyed by request_id, and its value contains the rest details as a dictionary.
            data_dict[request_id] = details
            # Open request log file and append to the end.
            with open(RECORD_FILE, mode="a") as f:
                json.dump(data_dict, f, indent=None)
                f.write('\n')
            await self.send_logs_user('%s requested a dreamie (%s) at %s' % (name, villager.capitalize(), timestring))

    @commands.command(name='status', aliases=['st'])
    async def status(self, ctx):
        '''Check the status of a user's request(s).'''
        # Retrieve data_dict from the request log file.
        data_dict = utils.open_requestlog()
        found = ""
        for request_id, details in list(data_dict.items()):
            for k, v in list(details.items()):
                if k == u'name' and ctx.message.author.name in v:
                    # also hide requests with status == 'cancel' or 'closed'
                    if details['status'] not in (utils.Status.CLOSED.name, utils.Status.CANCEL.name):
                        found += 'request_id: **%s**\n' % request_id
                        found += utils.printadict(details, hide_self=True)
                        found += '\n'
        if found:
            await ctx.send("Found your request")
            color = utils.status_color(details)
            em = utils.get_embed(color, found)
            await ctx.channel.send(embed=em)
        else:
            em = utils.get_embed('red', "You don\'t have any request.")
            await ctx.channel.send(embed=em)
            # await ctx.send("You don't have any request.")

    @commands.command(name='ready', aliases=['rdy'])
    async def ready(self, ctx, req_id):
        '''Send a note to the staff team when you are ready to accept a new villager.'''
        # Check if the requester matches.
        data_dict = utils.open_requestlog()
        dreamie = None
        found = None
        for request_id, details in list(data_dict.items()):
            if str(request_id) == str(req_id):
                # user can only mark their own request.
                for k, v in list(details.items()):
                    if k == u'name' and ctx.message.author.name in v:
                        found = ('%s has marked request **%s** as ready to '
                                 'accept the dreamie!' % (ctx.message.author.name, req_id))
                        # await ctx.send(message % (req_id, ctx.message.author.name))
                        details['status'] = utils.Status.READY.name
                        dreamie = details['villager']
                        dreamie = dreamie.split(',')[0]
                        # mark a last_modified timestring
                        tm = time.localtime(time.time())
                        timestring = time.strftime("%Y-%m-%d %I:%M:%S%p %Z", tm)
                        details['last_modified'] = timestring
                        break

        if found:
            color = utils.status_color(details)
            em = utils.get_embed(color, found)
            await ctx.channel.send(embed=em)
            utils.flush_requestlog(data_dict)
            await self.send_logs_user('%s is ready to accept a dreamie(%s).' % (ctx.message.author.name, dreamie))
        else:
            em = utils.get_embed('red', 'Cannot found your request %s.' % req_id)
            await ctx.channel.send(embed=em)
            return


    @commands.command(name='cancel', aliases=['can'])
    async def cancel(self, ctx, req_id):
        '''Cancel a request. <request ID> is required.'''
        # Check if the requester matches, or a staff can cancel.
        data_dict = utils.open_requestlog()

        # Setup a Flow controller.
        flow = request.Flow(self.bot, ctx)
        found = False
        for request_id, details in list(data_dict.items()):
            if str(request_id) == str(req_id):
                # user can only cancel their own request.
                for k, v in list(details.items()):
                    if k == u'name' and ctx.message.author.name in v:
                        message = 'You are about to cancel a request **%s**' % req_id
                        em = utils.get_embed('red', message, title='Cancel A Request')
                        await ctx.channel.send(embed=em)
                        found = True
                        # await ctx.send("Cancelled request %s by %s" % (req_id, ctx.message.author.name))
                        details['status'] = utils.Status.CANCEL.name
                        # mark a last_modified timestring
                        tm = time.localtime(time.time())
                        timestring = time.strftime("%Y-%m-%d %I:%M:%S%p %Z", tm)
                        details['last_modified'] = timestring
                        break
        if not found:
            message = 'Your request %s was not found.' % req_id
            em = utils.get_embed('red', message, title='Cannot Find Request')
            await ctx.channel.send(embed=em)
            return

        are_you_sure = await ctx.send(f":information_source: Please confirm YES/NO to cancel"
                                      f" this request **%s**" % request_id)

        reaction = await flow.get_yes_no_reaction_confirm(are_you_sure, 200)
        if reaction is None:
            return
        if not reaction:
            em = utils.get_embed('red', 'Aborted.')
            return await ctx.channel.send(embed=em)
            # return await ctx.send("Aborted.")
        elif reaction:
            utils.flush_requestlog(data_dict)
            await ctx.send(f"You\'ve cancelled this request.")
            await self.send_logs_user('Cancelled request %s by %s' % (req_id, ctx.message.author.name))


def setup(bot):
    bot.add_cog(User(bot))
    print('User module loaded.')
