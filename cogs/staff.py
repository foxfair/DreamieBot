import asyncio
import json
import os
import re
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
TIME_FORMAT = os.getenv('TIME_FORMAT')
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
            if not req_id or str(request_id).lower() == str(req_id).lower():
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

    @commands.command(
        name='review',
        aliases=['rev'],
        usage=('<req_id> will approve an application by its ID.\n'
               'To reject one, use "~review <req_id> denied"'))
    @is_staff
    async def review(self, ctx, req_id, denied=None):
        '''Review an application. The result is either approved or denied.'''
        data_dict = utils.open_requestlog()
        user_id = 0
        staff = None
        found = False
        found_data = dict()
        rejected = dict()
        for request_id, details in list(data_dict.items()):
            if str(request_id) == str(req_id):
                found = True
                staff = ctx.message.author.name
                staff += '#' + ctx.message.author.discriminator
                staff_obj = self.bot.get_user(ctx.message.author.id)
                user_id = details['user_id']
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
                    server_message = '%s denied an application: %s' % (staff,
                                                                       req_id)
                    details['status'] = utils.Status.REJECTED.name
                    # mark a last_modified timestring
                    tm = time.localtime(time.time())
                    timestring = time.strftime(TIME_FORMAT, tm)
                    details['last_modified'] = timestring
                    details['staff'] = staff
                    rejected[request_id] = details
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
                    details['status'] = utils.Status.APPROVED.name
                    # mark a last_modified timestring
                    tm = time.localtime(time.time())
                    timestring = time.strftime(TIME_FORMAT, tm)
                    details['last_modified'] = timestring
                    details['staff'] = staff
                    # send to log channel
                    await self.send_logs('%s approved an application: %s' %
                                         (staff, req_id))
                    # send a DM to note the user.
                    if user_id:
                        user = self.bot.get_user(user_id)
                        dm_chan = user.dm_channel or await user.create_dm()
                        user_msg = ('Your application **{}** is approved by a '
                                    'staff (_{}_).\nPlease use the `~status` '
                                    'command to check current status.'.format(
                                        req_id, staff))
                        await dm_chan.send(user_msg)
                # Save changes to found_data
                found_data[request_id] = details
        if not found:
            message = 'Cannot find application **%s**' % req_id
            await ctx.send(message)
            # send to log channel
            return await self.send_logs(message)
        # Write changes back.
        utils.flush_requestlog(data_dict)
        time.sleep(1)
        await sheet.update_data(found_data)
        if rejected:
            for k, _ in rejected.items():
                await sheet.archive_column(k)

    @commands.command(name='found', aliases=['fnd'])
    @is_staff
    async def found(self, ctx, req_id):
        '''Indicates that you have found a requested villager.'''
        data_dict = utils.open_requestlog()
        user_id = 0
        staff = ctx.message.author.name
        staff += '#' + ctx.message.author.discriminator
        staff_obj = self.bot.get_user(ctx.message.author.id)
        dreamie = ''
        found_data = dict()
        for request_id, details in list(data_dict.items()):
            if str(request_id) == str(req_id):
                message = 'A villager of this application **%s** was found by %s!'
                await ctx.send(message % (req_id, staff))
                details['status'] = utils.Status.FOUND.name
                dreamie = details['villager']
                # only get the name
                dreamie = dreamie.split(',')[0]
                # mark a last_modified timestring
                tm = time.localtime(time.time())
                timestring = time.strftime(TIME_FORMAT, tm)
                details['last_modified'] = timestring
                details['staff'] = staff
                user_id = details['user_id']
                found_data[request_id] = details

        utils.flush_requestlog(data_dict)
        time.sleep(1)
        await sheet.update_data(found_data)
        # send to log channel
        await self.send_logs('%s found a requested villager: %s' %
                             (staff, dreamie))
        # send a DM to note the user.
        if user_id:
            user = self.bot.get_user(user_id)
            dm_chan = user.dm_channel or await user.create_dm()
            message = ('%s your dreamie %s has been found.\nYou have 72hrs'
                       ' to get an open plot ready and use the **~ready** '
                       'command to notify us. You will be contacted by '
                       '%s to coordinate the following steps during your '
                       'selected timeslot.\nRequest Id: %s\n\n'
                       'If you do not get ready in time, this application '
                       'will expire automatically. Your villager will not '
                       'be held for you and will be passed to the next '
                       'applicant.\n')
            await dm_chan.send(message % (user.mention, dreamie,
                                          staff, req_id))

    @commands.command(name='close', aliases=['cls'])
    @is_staff
    async def close(self, ctx, req_id):
        '''Close an application and pop some firework.'''
        data_dict = utils.open_requestlog()
        user_id = 0
        staff = ctx.message.author.name
        staff += '#' + ctx.message.author.discriminator
        staff_obj = self.bot.get_user(ctx.message.author.id)
        villager = None
        found_data = dict()
        for request_id, details in list(data_dict.items()):
            if str(request_id) == str(req_id):
                message = 'Congrats! Application **%s** is now closed by %s!'
                villager = details['villager'].split(',')[0]
                await ctx.send(message % (req_id, staff))
                details['status'] = utils.Status.CLOSED.name
                # mark a last_modified timestring
                tm = time.localtime(time.time())
                timestring = time.strftime(TIME_FORMAT, tm)
                details['last_modified'] = timestring
                details['staff'] = staff
                user_id = details['user_id']
                found_data[request_id] = details

        utils.flush_requestlog(data_dict)
        time.sleep(1)
        await sheet.update_data(found_data)
        # Then hide the close row.
        await sheet.archive_column(req_id)

        # send to log channel
        await self.send_logs('%s closed an application: %s' % (staff, req_id))
        # send a DM to note the user.
        if user_id:
            user = self.bot.get_user(user_id)
            dm_chan = user.dm_channel or await user.create_dm()
            message = 'Congrats, %s! You have found your dreamie, %s.\n'
            message += 'Your application **%s** is closed by a staff (_%s_).\n'
            message += 'After you\'ve settled down, please consider showing '
            message += 'appreciation in the #Player-Feedback channel!'
            await dm_chan.send(message %
                               (user.mention, villager, req_id, staff))

    @commands.command(name='lock', aliases=['loc'])
    @is_staff
    async def lock(self, ctx):
        '''Lock the bot and reject any new application. Use it again to unlock.'''
        def get_state_text(state):
            "Wrapper function to get lock/unlock texts based on states."
            return 'lock' if state else 'unlock'

        # TODO: use asyncio.Lock() to acquire lock!
        # https://discordpy.readthedocs.io/en/latest/ext/tasks/
        staff = ctx.message.author.name
        staff += '#' + ctx.message.author.discriminator
        staff_obj = self.bot.get_user(ctx.message.author.id)
        # Setup a Flow controller.
        flow = request.Flow(self.bot, ctx)
        # Flip the bot status.
        current_state_text = get_state_text(self.is_bot_locked)
        next_state_text = get_state_text(not self.is_bot_locked)
        are_you_sure = await ctx.send(
            f":question: DreamieBot is currently {current_state_text}ed.\n"
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
                lock_activity = discord.Game(name='Locked All Applications',
                                             state='LOCKED')
                new_status = discord.Status.dnd
                await self.bot.change_presence(status=new_status,
                                               activity=lock_activity)
                await ctx.send(
                    f"You have locked the bot, use **~lock** command again to unlock it."
                )
            else:
                # Manually revert back to the original status=online.
                await self.bot.change_presence(
                    activity=discord.Game(f"Fostering Dreamies"), afk=True)
                await ctx.send(
                    f"You have unlocked the bot and it is back in business.")
        # send to log channel
        await self.send_logs('%s has **%sed** DreamieBot.' %
                             (staff, next_state_text))

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
        await ctx.send(message %
                       (user_obj.mention, user_id, channel_id, permission))
        # send to log channel
        log_message = 'Inspected user: name=%s, ID=%s. Channel ID: %s. Permission: %s.'
        await self.send_logs(log_message %
                             (name, user_id, channel_id, permission))

    @commands.command(name='claim')
    @is_staff
    async def claim(self, ctx, req_id):
        '''Claim an application to move its status to PROCESSING.'''
        data_dict = utils.open_requestlog()
        user_id = 0
        staff = ctx.message.author.name
        staff += '#' + ctx.message.author.discriminator
        staff_obj = self.bot.get_user(ctx.message.author.id)
        found_data = dict()
        for request_id, details in list(data_dict.items()):
            if str(request_id) == str(req_id):
                villager = details['villager'].split(',')[0]
                details['status'] = utils.Status.PROCESSING.name
                # mark a last_modified timestring
                tm = time.localtime(time.time())
                timestring = time.strftime(TIME_FORMAT, tm)
                details['last_modified'] = timestring
                details['staff'] = staff
                found_data[request_id] = details
                user_id = details['user_id']
                name = details['name']
                break
        # Send a note back to the staff.
        staff_msg = ('You claimed an application: %s (%s looks for %s).')
        await ctx.send(staff_msg % (req_id, name, villager))
        utils.flush_requestlog(data_dict)
        time.sleep(1)
        await sheet.update_data(found_data)
        # send to log channel
        await self.send_logs('%s claim an application: %s' % (staff, req_id))
        # send a DM to note the user.
        if user_id:
            user = self.bot.get_user(user_id)
            dm_chan = user.dm_channel or await user.create_dm()
            user_msg = (
                'Thank you for applying to the Dream Villager Adoption Program.'
                ' We have approved your application and a staff member of our '
                'team, _%s_, has begun looking for your dream villager.\n'
                'Please monitor your DMs for updates. You can use **~status** '
                'command to check the latest status.\n'
                'If you have any questions, please check the FAQ in '
                '_#villager-adoption-program, or ask questions in '
                '#villager-trading_, or ping us **@adoptionteam**.'
            )
            await dm_chan.send(user_msg % staff)

    @commands.command(name='search', aliases=['sea'], usage=(
            '<summary|status|name>. status could be any of pending, approved, '
            'reject, processing, found, ready, close or cancel. name could be '
            'either a full name with tag like "foxfair#2155" or just "foxfair"'
            ' and search all applications by this name in return.'), hidden=True)
    @is_staff
    async def search(self, ctx, *input_args):
        '''Search for a summary, status or name in all applications.'''
        data_dict = utils.open_requestlog()
        user_id = 0
        # Since this function is shared with a background task.
        # When ctx = None, it will not send the result messages to the user,
        # instead, it returns a dictionary.
        all_args = [a.lower() for a in list(input_args)]
        all_status = [t.name for t in utils.Status]
        tmp_dict = dict()
        target = all_args[0]
        if target == 'summary':
            total = len(data_dict)
            # We don't care about closed, cancel or rejected applications.
            for status in all_status:  # expected_status:
                tmp_dict[status] = 0
                for _, details in list(data_dict.items()):
                    if status == details['status']:
                        tmp_dict[status] += 1
                if tmp_dict[status]:
                    ratio = '{} ({:.3f}{})'.format(tmp_dict[status],
                            (tmp_dict[status]/total*100), '%')
                    tmp_dict[status] = ratio
                else:
                    tmp_dict[status] = '0 (------)'
            if not ctx:
                return tmp_dict
            embed = discord.Embed()
            embed.title = 'Applications Summary:'
            embed.color = utils.random_color()
            embed.description = 'Total Applications: %d' % total
            for k, v in tmp_dict.items():
                embed.add_field(name=k, value=v, inline=True)
            return await ctx.send(embed=embed)
        elif target.upper() in all_status:
            # Search by status
            target = target.upper()
            tmp_dict = dict()
            for request_id, details in list(data_dict.items()):
                if target == details['status']:
                    villager = details['villager'].split(', ')[0]
                    tmp_dict[request_id] = '**{}** looks for _{}_'.format(
                        details['name'], villager)
            # Prepare for background reporting task.
            if not ctx and 'background' in all_args:
                return tmp_dict
            if not ctx and 'countdown' in all_args:
                # For coutndown background tasks, we need to return a raw
                # details dict.
                raw_dict = dict()
                for request_id, details in list(data_dict.items()):
                    if target == details['status']:
                        raw_dict[request_id] = details
                return raw_dict
            title = '_%s_ Application' % target.capitalize()
            if len(tmp_dict) > 1:
                title += 's: *%d*' % len(tmp_dict)
            else:
                title += ': *%d*' % len(tmp_dict)
            if tmp_dict:
                embed = discord.Embed(title=title)
                embed.color = utils.random_color()
                for k, v in tmp_dict.items():
                    embed.add_field(name=k, value=v, inline=True)
                return await ctx.send(embed=embed)
            else:
                return await ctx.send('Found nothing for status=%s' % target)
        else:
            # Search by user, could be multiple names.
            # fix the guild if nothing found.
            # 704875142496649256 is Beyond Stalks.
            # guild_id = ctx.message.guild if ctx.message.guild else '704875142496649256'
            tmp_list = []
            for target in all_args:
                title = 'Search By Name: %s' % target
                found = dict()
                # user_id = discord.utils.get(client.get_all_members(), name=name_list[0],
                #                            discriminator=name_list[1]).id
                # pattern = re.search(target, details['name'], re.IGNORECASE)
                for request_id, details in list(data_dict.items()):
                    if re.search(target, details['name'], re.IGNORECASE):
                        villager = details['villager'].split(', ')[0]
                        status = 'Status: {}'.format(details['status'].capitalize())
                        found[request_id] = '**{}**\n{}'.format(villager, status)
                if found:
                    embed = discord.Embed(title=title)
                    embed.color = utils.random_color()
                    for k, v in found.items():
                        embed.add_field(name=k, value=v, inline=True)
                    return await ctx.send(embed=embed)
                else:
                    return await ctx.send('Found nothing for this name: %s' % target)
    
    @commands.command(name='archive', aliases=['ar'], hidden=True,
                      usage='<req_id> to hide a row of the application id.'
                            'Use anything after <req_id> will toggle and '
                            'unhide its row')
    @is_staff
    async def archive(self, ctx, req_id, *input_args):
        '''Archive and hide a row in the sheet by an application ID.'''
        data_dict = utils.open_requestlog()
        toggle = list(input_args)
        if not toggle:
            # always hide
            await sheet.archive_column(req_id)
        else:
            # unhide
            await sheet.archive_column(req_id, False)
        server_msg = 'DreamieBot archived a row of request_id %s in the sheet.'
        # send to log channel
        return await self.send_logs(server_msg % (req_id))


def setup(bot):
    bot.add_cog(Staff(bot))
    print('Staff module loaded.')
