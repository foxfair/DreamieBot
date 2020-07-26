'''Checking module for permission level and generic routines.'''

import os
import re

from discord.ext import commands
from dotenv import load_dotenv

from ext import utils
from ext import auth_config

load_dotenv()

# How many requests does a user can ask
REQUEST_LIMIT = int(os.getenv('REQUEST_LIMIT'))
VILLAGER_NAMES = os.getenv('VILLAGER_NAMES')


def precheck(user, villager):
        '''Precheck steps before processing requests.'''
        data_dict = utils.open_requestlog()
        # Precheck will fail when either one of these conditions is met:
        # - The user requested this villager before, so this is a duplicated check.
        # - The user has too many requests. See the default in REQUEST_LIMIT=1.
        message = ''
        villagers = []
        last_rejected = []
        for request_id, details in list(data_dict.items()):
            if details['name'] == str(user) and (details['villager'] == villager):
                message = 'You have requested a duplicated villager, check your application with ~status.'
                return message
            for k, v in list(details.items()):
                if (str(k) == 'name' and user in v and (details['status'] not in (
                        utils.Status.CLOSED.name, utils.Status.CANCEL.name, utils.Status.REJECTED.name))):
                    villagers.append(str(details['villager']))
                # if (str(k) == 'name' and user in v and (details['status']
        # Use re.match to search pattern here.
        pattern = re.compile(str(villager).lower())
        for v in villagers:
            if pattern.search(v):
                message = 'You requested **%s** before, please use *"~status"*'
                message += ' command to get previous application ID.'
                return message % villager
        if len(villagers) >= REQUEST_LIMIT:
            message = 'You hit the max application number (%d) per user.'
            message += '\nPlease work with the Villager Adoption Team to '
            message += 'fulfill your current application first.'
            return message % REQUEST_LIMIT


def validate_name(villager):
    '''Validate a villager's name from a static file.'''
    message = None
    found = False
    if ' ' in villager:
        tmp = []
        for v in villager.split(' '):
            tmp.append(v.capitalize())
        villager = ' '.join(tmp)
    # This method is not very scalable, if a new villager is added we will need
    # to update the static file.
    with open(VILLAGER_NAMES) as f:
        pattern = re.compile(r'%s' % villager)
        content = f.read().split('\n')
        for line in content:
            if re.fullmatch(pattern, line):
                found = True
        if not found:
            message = '**%s** is not a valid villager name.'
            return message % villager


def is_staff():
    async def predicate(ctx):
        if ctx.author.id in auth_config.AUTHORIZED:
            return True
        else:
            return False
    return commands.check(predicate)


def find_staff_id(bot, name):
    '''Pass a name(foxfair#2155) in and find its discord.User id.'''
    found = None
    staff_dict = dict()
    for staff_id in auth_config.AUTHORIZED:
        staff = bot.get_user(staff_id)
        name = '{}#{}'.format(staff.name, staff.discriminator)
        staff_dict[staff_id] = name
    for k, v in staff_dict.items():
        if str(name) in v:
            found = k
            break
    return found
