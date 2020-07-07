'''A collection of utility functions.'''

from enum import Enum

import json
import os
import random
import time

import discord
from discord.ext import commands
from dotenv import load_dotenv

# from cogs import request
from ext import auth_config

load_dotenv()
# Sitting in the parent directory where bot.py runs.
RECORD_FILE = os.getenv('RECORD_FILE')


class Status(Enum):
    '''Status for a request.'''
    # The default status of every new request, which is unreviewed and not approved yet.
    PENDING = 1

    # When a staff has reviewed and approved a request, the status is changed to processing.
    PROCESSING = 2

    # A staff has found a requested villager.
    FOUND = 3

    # The request has been fulfilled and closed.
    CLOSED = 4

    # A user indicates that there is an open plot, will be ready to welcome a dreamie home.
    READY = 5

    # A request is cancelled before completion. It is either cancelled by a user or a staff.
    CANCEL = 6


def open_requestlog():
    # Open request log file.
    data_dict = dict()
    with open(RECORD_FILE) as f:
        # data_dict is keyed by request_id, and its value contains the rest data.
        for line in f:
            line_dict = json.loads(line.rstrip())
            data_dict[list(line_dict)[0]] = list(line_dict.values())[0]
    return data_dict


def flush_requestlog(data):
    '''Use this function to write modified data back.'''
    os.remove(RECORD_FILE)
    time.sleep(1)
    with open(RECORD_FILE, mode='a') as f:
        for d in list(data.items()):
            tmp_dict = dict()
            tmp_dict[d[0]] = d[1]
            json.dump(tmp_dict, f, indent=None)
            f.write('\n')


def printadict(data_dict, hide_self=False):
    '''Convert a dictionary into a printable string.'''
    data = data_dict.copy()
    if hide_self:
        # when a user has multiple requests, hide these repeated information
        # Or anything we don't want users to see.
        try:
            del data['name']
            del data['user_id']
        except KeyError as e:
            print('printadict errors: %s', str(e))

    #return json.dumps(data, indent=2)
    tmp = []
    for k, v in data.items():
        tmp.append('{}: {}'.format(k, v))
    return '\n'.join(tmp)
    

def get_embed(color, text, title=None):
    '''Get an embedded object to send via bot.'''
    # For a finished adoption request. Usually it will be closed soon.
    if color == 'green':
        colour = discord.Colour.green()
    # For fostering.
    if color == 'orange':
        colour = discord.Colour.dark_orange()
    # For any system warning/error, and non-TT requests.
    if color == 'red':
        colour = discord.Colour.red()
    # Informational, and the default status color.
    if color == 'gray':
        colour = discord.Colour.dark_grey()
    # approved reqests.
    if color == 'gold':
        colour = discord.Colour.gold()
    # Staff special
    if color == 'purple':
        colour = discord.Colour.purple()

    if color == 'dark_green':
        colour = discord.Colour.dark_green()

    em = discord.Embed()
    em.description = text
    em.color = colour
    em.title = title if title else None
    return em


def status_color(data):
    '''Select embed color by the status of a data dictionary.'''
    # default = gray. status=PENDING 
    color = 'gray'

    # PROCESSING = gold
    if data['status'] == Status.PROCESSING.name:
        color = 'gold'
    # FOUND = orange
    if data['status'] == Status.FOUND.name:
        color = 'orange'

    # CANCEL = red
    if data['status'] == Status.CANCEL.name:
        color = 'red'

    # READY, CLOSED = green, dark_green
    if data['status'] == Status.READY.name:
        color = 'green'

    if data['status'] == Status.CLOSED.name:
        color = 'dark_green'

    return color


# from https://github.com/cree-py/RemixBot/blob/master/ext/utils.py
def paginate(text: str):
    '''Simple generator that paginates text.'''
    last = 0
    pages = []
    for curr in range(0, len(text)):
        if curr % 1980 == 0:
            pages.append(text[last:curr])
            last = curr
            appd_index = curr
    if appd_index != len(text) - 1:
        pages.append(text[last:curr])
    return list(filter(lambda a: a != '', pages))


def random_color():
    color = ('#%06x' % random.randint(8, 0xFFFFFF))
    color = int(color[1:], 16)
    color = discord.Color(value=color)
    return color
