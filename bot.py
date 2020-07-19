# Main file for the bot.
import ast
import datetime
import inspect
import json
import logging
import os

import discord
import aiohttp
import asyncio

from dotenv import load_dotenv
from discord.ext import commands

from ext import auth_config
from ext import checks
from ext import utils

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
# GUILD = os.getenv('DISCORD_GUILD')
BOT_DESC = os.getenv('BOT_DESC')
INVITE_URL = 'https://discord.com/api/oauth2/authorize?client_id=725436099018883153&permissions=216128&scope=bot'
# What bot.change_presence will show in the available state.
BOT_AVAIL_STATUS = 'Fostering Dreamies'

# If this prefix gets changed, change it in on_message() as well.
BOT_PREFIX = {'user': '~', 'admin': '+'}

# The Dreamie Bot starts here.
bot = commands.Bot(command_prefix=BOT_PREFIX.values(),
                   owner_id=auth_config.OWNER)
all_extensions = [
    x.replace('.py', '') for x in os.listdir('cogs') if x.endswith('.py')
]

# loggers start here. NOTE: logs/ should exist.
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='logs/discord.log',
                              encoding='utf-8',
                              mode='w')
handler.setFormatter(
    logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Another logger for bot behavior.
logger = logging.getLogger('bot')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='logs/bot.log',
                              encoding='utf-8',
                              mode='w')
handler.setFormatter(
    logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# What command we want to provide in this bot:
# For users they can use these commands:
#   'apply': Apply to request a new villager. The bot should generate an application ID and send back to user.
#   'status': to check the status of their requests. Status enum(Enumerated type) are:
#     ['PENDING', 'PROCESSING', 'FOUND', 'CLOSED', 'READY', 'CANCEL']
#     PENDING: The default status of every new request, which is unreviewed and not approved yet.
#     PROCESSING: When a staff has reviewed and approved a request, the status is changed to processing.
#     FOUND: A staff has found a requested villager and fostered to wait for an open plot.
#     CLOSED: The application has been fulfilled and closed.
#     READY: A user indicates that there is an open plot, will be ready to welcome a dreamie home.
#     CANCEL: An application is cancelled before completion. It is either cancelled by a user or
#       reviewed then denied by a staff.
#   'ready': to indicate the user is ready now or in the next three days. Required argument: an application ID.
#   'cancel': to cancel a request. Required argument: an application ID.
# ========================================================
# For staff, we can do these:
#   'list': List all requests or a specified request. Including cancelled and closed requests.
#   'review': Review an application to approve or deny, so that move it to the next state (ready to
#       proceed & recruit a villager for them). Required argument: an application ID.
#   'found': A staff has found a villager, and moved into a fostering house. Required argument: an application ID.
#   'close': Close a request. Required argument: an application ID.


def load_extension(cog, path='cogs.'):
    members = inspect.getmembers(cog)
    for name, member in members:
        if name.startswith('on_'):
            bot.add_listener(member, name)
    try:
        bot.load_extension(f'{path}{cog}')
    except Exception as e:
        print(f'LoadError: {cog}\n{type(e).__name__}: {e}')
        logger.warning('LoadError: %s', str(e))


def load_extensions(cogs, path='cogs.'):
    for cog in cogs:
        members = inspect.getmembers(cog)
        for name, member in members:
            if name.startswith('on_'):
                bot.add_listener(member, name)
        try:
            bot.load_extension(f'{path}{cog}')
        except Exception as e:
            print(f'LoadError: {cog}\n{type(e).__name__}: {e}')
            logger.warning('LoadError: %s', str(e))


load_extensions(all_extensions)


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(BOT_AVAIL_STATUS),
                              afk=True)
    _uptime = datetime.datetime.utcnow()
    url = f"https://discordbots.org/api/bots/{bot.user.id}/stats"

    bot._last_result = None
    bot.session = aiohttp.ClientSession()

    print(f'{bot.user.name} has connected to Discord@{_uptime}!')
    logger.info('Connected to Discord.')
    for guild in bot.guilds:
        logger.info('Joined this guild: %s(%d)' % (guild.name, guild.id))


@bot.event
async def on_message(message):
    if message.content.startswith('~'):
        if isinstance(message.channel, discord.DMChannel):
            await bot.process_commands(message)
        else:
            await message.channel.send('Only accept bot commands in DMs.')
    if message.content.startswith(
            '+') or message.channel.id in auth_config.SEND_MSG_CHANNELS:
        # Staff has priviledges.
        await bot.process_commands(message)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.DisabledCommand):
        em = utils.get_embed('red',
                             f'_{ctx.command}_ command has been disabled.')
        await ctx.send(embed=em)
    elif isinstance(error, commands.MissingRequiredArgument):
        em = utils.get_embed(
            'red', f'_{ctx.command}_ command missed a required argument.\n'
                    'Please use *~help <command>* to see what is missing.')
        await ctx.send(embed=em)

    elif isinstance(error, commands.BadArgument):
        em = utils.get_embed(
            'red', f'_{ctx.command}_ command called a bad argument.\n'
                    'Please use *~help <command>* to see what is missing.')
        await ctx.send(embed=em)
    else:
        await ctx.send(error)


@bot.event
async def on_guild_join(guild):
    '''Log when joins a server.'''
    logger.info('Joined a guild %s(%d), owner_id(%d), description(%s)',
                guild.name, guild.id, guild.owner_id, guild.description)


@bot.event
async def on_guild_remove(guild):
    '''Log when leaves a server.'''
    logger.info('Removed by a guild %s(%d), owner_id(%d), description(%s)',
                guild.name, guild.id, guild.owner_id, guild.description)


@bot.command(name='ping')
async def ping(ctx):
    '''Pong! Get the bot's response time'''
    em = utils.get_embed('green', f'{bot.latency * 1000} ms', title='Pong!')
    await ctx.send(embed=em)
    for guild in bot.guilds:
        print('Joined this guild: %s(%d)' % (guild.name, guild.id))


@bot.command(name='invite')
async def invite(ctx):
    '''Invite the bot to your server'''
    em = utils.get_embed('gray',
                         f'Invite me to your server: {INVITE_URL}',
                         title='Invite me!')
    await ctx.send(embed=em)


@bot.command(hidden=True)
@commands.is_owner()
async def reload(ctx, cog=None):
    """Reloads a cog"""
    cog = cog or 'all'
    if cog.lower() == 'all':
        for cog in all_extensions:
            try:
                bot.unload_extension(f"cogs.{cog}")
            except Exception as e:
                await ctx.send(
                    f"An error occured while reloading {cog}, error details: \n ```{e}```"
                )
        load_extensions(all_extensions)
        return await ctx.send(
            'All cogs updated successfully :white_check_mark:')
    if cog not in all_extensions:
        return await ctx.send(f'Cog {cog} does not exist.')
    try:
        bot.unload_extension(f"cogs.{cog}")
        await asyncio.sleep(1)
        load_extension(cog)
    except Exception as e:
        await ctx.send(
            f"An error occured while reloading {cog}, error details: \n ```{e}```"
        )
    else:
        await ctx.send(
            f"Reloaded the {cog} cog successfully :white_check_mark:")


@bot.command(name='shutdown', aliases=['shut'], hidden=True)
@commands.is_owner()
async def shutdown(ctx):
    '''Shut down the bot'''
    async def close():
        await bot.session.close()
        return await bot.logout()

    logger.info('Disconnected from Discord. Shutting down the bot.')
    em = utils.get_embed('red', 'Shutting down....', title='Offline!')
    await ctx.send(embed=em)
    # Release logger resource.
    for h in logger.handlers:
        h.close()
        logger.removeHandler(h)
    return await close()


if __name__ == '__main__':
    bot.run(TOKEN)
