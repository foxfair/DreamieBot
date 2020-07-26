'''A collection of utility functions.'''
# Note: secrets module is in Python 3.6+.
import datetime
from enum import Enum
import json
import os
import random
import secrets
import string
import time

import discord
from discord.ext import commands
from dotenv import load_dotenv

from ext import auth_config

load_dotenv()
# Sitting in the parent directory where bot.py runs.
RECORD_FILE = os.getenv('RECORD_FILE')


class Status(Enum):
    '''Status for a request.'''
    # The default status of every new request, which is unreviewed and not approved yet.
    PENDING = 1

    # When a staff has claimed an application.
    PROCESSING = 2

    # A staff has found a requested villager.
    FOUND = 3

    # The request has been fulfilled and closed.
    CLOSED = 4

    # A user indicates that there is an open plot, will be ready to welcome a dreamie home.
    READY = 5

    # An application is cancelled before completion. It is cancelled by a user.
    CANCEL = 6

    # An application has been reviewed then approved.
    APPROVED = 7

    # An application is rejected due to lack of community activities.
    REJECTED = 8

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

    # return json.dumps(data, indent=2)
    tmp = []
    for k, v in data.items():
        tmp.append('{}: {}'.format(k, v))
    return '\n'.join(tmp)


def form_text(details):
    '''Form embedded texts from details dictionary.'''
    try:
        last_mod = details['last_modified']
    except KeyError:
        # a data without last_modified is ok.
        last_mod = details['created_time']
    text = '{}\n{}\n{}'.format(details['name'],
                                details['villager'].split(',')[0], last_mod)
    return text


def genreport(data_dict, criteria=None):
    '''Generate a search/summary report.'''
    data = data_dict.copy()
    table_dict = dict()
    total = len(data)
    if not criteria:
        # summary report
        all_status = [str(e.name) for e in Status]
        tmp = dict()
        table_dict['All'] = '{} ({}%)'.format(total, 100)
        for status in all_status:
            tmp.setdefault(status, 0)
            for _, details in data.items():
                if details['status'] == status:
                    tmp[status] += 1
            tmp_value = tmp[status]
            if tmp_value == 0:
                ratio_text = '- (-------)'
            else:
                ratio_tmp = str('%.3f' % (tmp_value/total)) + '%'
                ratio_text = '%d (%s)' % (tmp_value, ratio_tmp)
            table_dict[status] = ratio_text
        # TODO: deal with time delta.
    else:
        # search by criteria and generate a report.
        for request_id, details in data.items():
            if criteria in str(details['status']):
                table_dict[request_id] = form_text(details)
    return table_dict


def get_embed(color, text, title=None):
    '''Get an embedded object to send via bot.'''
    # For a finished adoption request. Usually it will be closed.
    if color == 'green':
        colour = discord.Colour.green()
    # For found applications while fostering.
    if color == 'orange':
        colour = discord.Colour.dark_orange()
    # For rejected applications, and any system warning/error.
    if color == 'red':
        colour = discord.Colour.red()
    # Informational, and the default status color.
    if color == 'gray':
        colour = discord.Colour.dark_grey()
    # processing applications.
    if color == 'gold':
        colour = discord.Colour.gold()
    # Staff special
    if color == 'purple':
        colour = discord.Colour.purple()
    # The application is ready.
    if color == 'dark_green':
        colour = discord.Colour.dark_green()
    # approved applications.
    if color == 'skyblue':
        colour = discord.Colour.from_rgb(0,191,255)

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
    # CANCEL = red ?
    if data['status'] == Status.CANCEL.name:
        color = 'red'
    # READY = green
    if data['status'] == Status.READY.name:
        color = 'green'
    # CLOSED = darkgreen
    if data['status'] == Status.CLOSED.name:
        color = 'dark_green'
    # APPROVED = blue
    if data['status'] == Status.APPROVED.name:
        color = 'skyblue'
    # REJECTED= red
    if data['status'] == Status.REJECTED.name:
        color = 'red'
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


def generate_id(data_dict):
    '''Use a secure way to generate a non-conflict application id.'''
    app_id = None
    while True:
        app_id = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        if app_id not in data_dict:
            return app_id


# Credit to: https://stackoverflow.com/questions/18470627/how-do-i-remove-the-microseconds-from-a-timedelta-object
def chop_microseconds(delta):
    return delta - datetime.timedelta(microseconds=delta.microseconds)
