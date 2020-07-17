import asyncio
import json
import os
import re
import time

import discord
from discord.ext import commands
from dotenv import load_dotenv

from cogs import request
from ext import checks
from ext import sheet
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

    @commands.command(name='apply',
                      aliases=['app'],
                      usage='<villager name>, i.e: ~apply Raymond')
    async def apply(self, ctx, villager=None):
        '''Apply to request a villager and get an <application ID> in return.'''

        # Setup a Flow controller.
        flow = request.Flow(self.bot, ctx)
        # Find is_bot_locked from Staff cog.
        staff_cog = self.bot.get_cog('Staff')
        if staff_cog.is_bot_locked:
            text = 'I am sorry but the application queue is now locked and '
            text += 'cannot accept any application.\nPlease stay tuned in the '
            text += '#villager-adoption-program channel for future updates.'
            em = utils.get_embed('gold', text)
            return await ctx.channel.send(embed=em)
        if not villager:
            text = 'Greetings! Which villager would you like to request?\n'
            text += 'Use **~apply <villager>** command to create an application.'
            em = utils.get_embed('gray', text)
            return await ctx.channel.send(embed=em)
        # Viallger name differeniation: some villagers have a space char
        # between its names:
        v = villager.lower()
        if v is not 'kidd' and v in ('kid', 'agent', 'big', 'wart'):
            if v == 'kid':
                villager = 'Kid Cat'
                villager_link = 'https://villagerdb.com/villager/kid-cat'
            if v == 'agent':
                villager = 'Agent S'
                villager_link = 'https://villagerdb.com/villager/agent-s'
            if v == 'big':
                villager = 'Big Top'
                villager_link = 'https://villagerdb.com/villager/big-top'
            if v == 'wart':
                villager = 'Wart Jr.'
                villager_link = 'https://villagerdb.com/villager/wart-jr'
        else:
            # Form a villager link
            villager_link = 'https://villagerdb.com/villager/{}'.format(
                villager.lower())
            villager = villager.capitalize()
        # Validate the villager's name before everything.
        result = checks.validate_name(villager)
        if result:
            return await ctx.send(result)
        villager_data = "{}, {}".format(villager, villager_link)

        request_id = ctx.message.id
        name = ctx.message.author.name
        name += '#' + ctx.message.author.discriminator
        message = checks.precheck(name, villager)
        if message:
            em = utils.get_embed('red', message, title='Precheck Failed')
            return await ctx.channel.send(embed=em)

        tm = time.localtime(time.time())
        timestring = time.strftime("%Y-%m-%d %I:%M:%S%p %Z", tm)
        # init data and data_dict
        # data might be redundant because I use data_dict mostly.
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
        # default null for these two.
        details['last_modified'] = ''
        details['staff'] = ''

        em = utils.get_embed('gray', 'Your Application Details:')
        await ctx.channel.send(embed=em)
        await ctx.channel.send(utils.printadict(details, hide_self=True))
        time.sleep(1)
        # Flow control.
        tt_or_not = await ctx.send(
            f":information_source: Are you willing to do Time Travel in order to "
            f"make the process quicker?")
        tt_reaction = await flow.get_yes_no_reaction_confirm(tt_or_not, 200)
        if tt_reaction is None:
            return ctx.send(
                "Application cancelled. You may apply again at any time.")
        if not tt_reaction:
            details['can_time_travel'] = False
            # Only accept non-tter with an open plot in 72 hours to apply.
            within_72_hr = await ctx.send(
                f":question: Will you have an open plot with 72 hours? ")
            reaction = await flow.get_yes_no_reaction_confirm(
                within_72_hr, 200)
            if reaction is None:
                return ctx.send(
                    "Application cancelled. You may apply again when an open plot is ready."
                )
            if not reaction:
                rejected_text = (
                    "We’re sorry, your application cannot be accepted at this time.\n"
                    "Please apply again when you are within a 72 hour window "
                    "of an open plot.")
                em = utils.get_embed('red',
                                     rejected_text,
                                     title="Application Denied")
                return await ctx.channel.send(embed=em)
        else:
            details['can_time_travel'] = True

        # Available timeslot selection
        timeslot = await ctx.send(
            f":information_source: Which time slot is the best choice to contact you"
            " if we have to? \n"
            "NOTE: Please refer to https://time.is/UTC and select your most available"
            " timeslot in **UTC**.\n"
            ":sparkles: Slot 1: 00:00 - 03:59 UTC.\n:eight_spoked_asterisk: "
            "Slot 2: 04:00 - 07:59 UTC.\n"
            ":heart: Slot 3: 08:00 - 11:59 UTC.\n:rocket: Slot 4: 12:00 - 15:59 UTC.\n"
            ":crescent_moon: Slot 5: 16:00 - 19:59 UTC.\n:full_moon: Slot 6: "
            "20:00 - 23:59 UTC.\n")
        time.sleep(1)
        slot_reaction = await flow.get_timeslot_reaction_confirm(timeslot, 600)
        if slot_reaction is None:
            return ctx.send(
                "Application cancelled. You may apply again at any time.")
        if slot_reaction == 1:
            details['avail_time'] = '00:00-03:59 UTC'
        if slot_reaction == 2:
            details['avail_time'] = '04:00-07:59 UTC'
        if slot_reaction == 3:
            details['avail_time'] = '08:00-11:59 UTC'
        if slot_reaction == 4:
            details['avail_time'] = '12:00-15:59 UTC'
        if slot_reaction == 5:
            details['avail_time'] = '16:00-19:59 UTC'
        if slot_reaction == 6:
            details['avail_time'] = '20:00-23:59 UTC'

        # Final confirmation
        are_you_sure = await ctx.send(
            f":question: Please confirm YES/NO to create a new "
            f"application of finding **%s**" % villager)

        reaction = await flow.get_yes_no_reaction_confirm(are_you_sure, 200)
        if reaction is None:
            return ctx.send(
                "Application cancelled. You may apply again at any time.")
        if not reaction:
            return await ctx.send("Aborted your application.")
        elif reaction:
            user_obj = self.bot.get_user(ctx.message.author.id)
            await ctx.send("This application has been logged for review.")
            await ctx.send(
                "%s Please take a note of your application ID:\n**%s**" %
                (user_obj.mention, request_id))
            time.sleep(1)
            # Add a default status.
            data += u"Status: {}".format(utils.Status.PENDING.name)
            details['status'] = utils.Status.PENDING.name

            # data_dict is keyed by request_id, and its value contains the rest details as a dictionary.
            data_dict[request_id] = details
            # Open request log file and append to the end.
            with open(RECORD_FILE, mode="a") as f:
                json.dump(data_dict, f, indent=None)
                f.write('\n')
            sheet.update_data(data_dict)
            await self.send_logs_user('%s requested a dreamie (%s) at %s' %
                                      (name, villager.capitalize(), timestring)
                                      )

    @commands.command(name='status', aliases=['st'])
    async def status(self, ctx):
        '''Check the status of a user's application.'''
        # Retrieve data_dict from the request log file.
        data_dict = utils.open_requestlog()
        found = ""
        for request_id, details in list(data_dict.items()):
            for k, v in list(details.items()):
                if k == u'name' and ctx.message.author.name in v:
                    # also hide requests with status == 'cancel' or 'closed'
                    if details['status'] not in (utils.Status.CLOSED.name,
                                                 utils.Status.CANCEL.name):
                        found += 'application_id: **%s**\n' % request_id
                        found += utils.printadict(details, hide_self=True)
                        found += '\n'
        if found:
            await ctx.send("Found your application:")
            color = utils.status_color(details)
            em = utils.get_embed(color, found)
            await ctx.channel.send(embed=em)
        else:
            em = utils.get_embed('red', "You don\'t have any application.")
            await ctx.channel.send(embed=em)

    @commands.command(name='ready', aliases=['rdy'])
    async def ready(self, ctx, req_id):
        '''Send a note to the staff team when you are ready to accept a new villager.'''
        # Check if the requester matches.
        data_dict = utils.open_requestlog()
        dreamie = None
        found = None
        found_data = dict()

        # Setup a Flow controller.
        flow = request.Flow(self.bot, ctx)

        for request_id, details in list(data_dict.items()):
            if str(request_id) == str(req_id):
                # user can only mark their own request.
                for k, v in list(details.items()):
                    if k == u'name' and ctx.message.author.name in v:
                        found = (
                            '%s has marked the application **%s** as ready to '
                            'accept the dreamie!' %
                            (ctx.message.author.name, req_id))
                        details['status'] = utils.Status.READY.name
                        dreamie = details['villager']
                        dreamie = dreamie.split(',')[0]
                        # mark a last_modified timestring
                        tm = time.localtime(time.time())
                        timestring = time.strftime("%Y-%m-%d %I:%M:%S%p %Z",
                                                   tm)
                        details['last_modified'] = timestring
                        found_data[request_id] = details
                        break

        if not found:
            em = utils.get_embed('red',
                                 'Cannot found your application %s.' % req_id)
            await ctx.channel.send(embed=em)
            return

        are_you_sure = await ctx.send(
            f":information_source: Please confirm YES/NO to indicate"
            f" that you have an open plot ready to receive your dreamie.\n"
            f"Application ID:**%s**" % request_id)
        reaction = await flow.get_yes_no_reaction_confirm(are_you_sure, 200)

        if reaction is None:
            return
        if not reaction:
            em = utils.get_embed('red', 'Aborted.')
            return await ctx.channel.send(embed=em)
        elif reaction:
            color = utils.status_color(details)
            em = utils.get_embed(color, found)
            await ctx.channel.send(embed=em)
            utils.flush_requestlog(data_dict)
            sheet.update_data(found_data)
            await self.send_logs_user('%s is ready to accept a dreamie (%s).' %
                                      (ctx.message.author.name, dreamie))
            # TODO: add staff dm here.

    @commands.command(name='cancel', aliases=['can'])
    async def cancel(self, ctx, req_id):
        '''Cancel an application. <application ID> is required.'''
        # Check if the requester matches, or a staff can cancel.
        data_dict = utils.open_requestlog()

        # Setup a Flow controller.
        flow = request.Flow(self.bot, ctx)
        found = False
        found_data = dict()
        for request_id, details in list(data_dict.items()):
            if str(request_id) == str(req_id):
                # user can only cancel their own request.
                for k, v in list(details.items()):
                    if k == u'name' and ctx.message.author.name in v:
                        message = 'You are about to cancel an application **%s**' % req_id
                        em = utils.get_embed('red',
                                             message,
                                             title='Cancel An Application')
                        await ctx.channel.send(embed=em)
                        found = True
                        details['status'] = utils.Status.CANCEL.name
                        # mark a last_modified timestring
                        tm = time.localtime(time.time())
                        timestring = time.strftime("%Y-%m-%d %I:%M:%S%p %Z",
                                                   tm)
                        details['last_modified'] = timestring
                        found_data[request_id] = details
                        break
        if not found:
            message = 'Your application %s was not found.' % req_id
            em = utils.get_embed('red', message, title='Application Not Found')
            await ctx.channel.send(embed=em)
            return

        are_you_sure = await ctx.send(
            f":information_source: Please confirm YES/NO to cancel"
            f" this application **%s**" % request_id)

        reaction = await flow.get_yes_no_reaction_confirm(are_you_sure, 200)
        if reaction is None:
            return
        if not reaction:
            em = utils.get_embed('red', 'Aborted.')
            return await ctx.channel.send(embed=em)
        elif reaction:
            utils.flush_requestlog(data_dict)
            await ctx.send(f"You\'ve cancelled this application.")
            await self.send_logs_user('Cancelled application %s by %s' %
                                      (req_id, ctx.message.author.name))
            sheet.update_data(found_data)


def setup(bot):
    bot.add_cog(User(bot))
    print('User module loaded.')
