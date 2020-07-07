'''Modify applicant data in a Google Sheet by the bot.'''
import gspread
from gspread_formatting import *

from ext import utils

# Sheet ID in the url, just behind https://docs.google.com/spreadsheets/d/<ID is here>
GSHEET_ID='1rrwexbsVgOoKslDllp7-Sc0TPwoJxP9W_yKesg02tpo'
# Or if the spreadhseet has been shared with you, you can search by its title.
GSHEET_TITLE='Test discordbot-updater sheets'
# Which worksheet will the bot modify
GSHEET_WORKSHEET='Sheet1'

gc = gspread.service_account()

# Open a sheet from a spreadsheet in one go
sheet = gc.open(GSHEET_TITLE)
wks = sheet.worksheet(GSHEET_WORKSHEET)


def format_color(status, time_travel=False):
    '''Format different colors by status.'''
    cell_color = None
    # Setup dictionaries of cell formats.
    text_format = dict()
    tmp = dict()
    tmp['fontFamily'] = 'Arial'
    tmp['fontSize'] = 10
    text_format['textFormat'] = tmp

    red_text_format = text_format.copy()
    tmp_red = red_text_format['textFormat']
    tmp_red ['foregroundColor'] = {
        'red': 1}

    # Status = PENDING, it is also the base of other colors.
    cell_white = dict()
    cell_white['horizontalAlignment'] = 'center'
    cell_white['verticalAlignment'] = 'bottom'
    cell_white['wrapStrategy'] = 'OVERFLOW_CELL'
    cell_white['hyperlinkDisplayType'] = 'PLAIN_TEXT'
    cell_white['backgroundColor'] = {
        'red': 1,
        'green': 1,
        'blue': 1}

    # Status = PROCESSING
    cell_yellow = cell_white.copy()
    cell_yellow['backgroundColor'] = {
        'red': 1,
        'green': 1}

    # Status = FOUND
    cell_orange = cell_white.copy()
    cell_orange['backgroundColor'] = {
        'red': 1,
        'green': 0.6}

    # Status = CLOSED
    cell_green = cell_white.copy()
    cell_green['backgroundColor'] = {
        'red': 0,
        'green': 1}

    # Status = READY [user is ready].
    cell_greenaccent = cell_white.copy()
    cell_greenaccent['backgroundColor'] = {
        'red': 0.20392157,
        'green': 0.65882355,
        'blue': 0.3254902}

    # Status = CANCEL [user or staff cancelled a request]
    cell_gray = cell_white.copy()
    cell_gray['backgroundColor'] = {
        'red': 0.6,
        'green': 0.6,
        'blue': 0.6}

    if str(time_travel).lower() == 'false':
        red_text_format = red_text_format
    else:
        red_text_format = None

    if status == utils.Status.PENDING.name:
        cell_color = cell_white
    if status == utils.Status.PROCESSING.name:
        cell_color = cell_yellow
    if status == utils.Status.FOUND.name:
        cell_color = cell_orange
    if status == utils.Status.CLOSED.name:
        cell_color = cell_green
    if status == utils.Status.READY.name:
        cell_color = cell_greenaccent
    if status == utils.Status.CANCEL.name:
        cell_color = cell_gray
    return (cell_color, red_text_format)


def update_data(data):
    '''Update a single row in the spreadsheet and fill changes up with passed data.'''
    last_modified = ''
    new_data = []
    for request_id, details in data.items():
        new_data.append(str(request_id))
        new_data.append(details['name'])
        new_data.append(details['status'])
        villager = details['villager']
        # only need the name put in the sheet.
        new_data.append(villager.split(',')[0])
        new_data.append(details['created_time'])
        new_data.append(details['can_time_travel'])
        new_data.append(details['avail_time'])
        try:
            new_data.append(details['last_modified'])
        except KeyError:
            # normal case: some requests don't have a last_modified data yet.
            pass

    try:
        # Updating an existing data.
        cell = wks.find(str(request_id))
        row = cell.row
        for i in range(1, len(new_data)+1):
            wks.update_cell(row, i, new_data[i-1])
        wks.format('A:H', {"horizontalAlignment": "CENTER"})
        # TODO: add comment/note to status field and record the latest change.
        (color, red_text) = format_color(details['status'],
                                 details['can_time_travel'])
        data_range = 'A{}:H{}'.format(row, row)
        # Update color and text format.
        wks.format(data_range, color)
        if red_text:
            wks.format(data_range, red_text)
    except gspread.exceptions.CellNotFound:
        # Appending new data
        all_data = wks.get_all_records()
        if not all_data:
        # write headers first..
            wks.append_row(['Request Id', 'Name', 'Status', 'Villager',
                            'Created Time(UTC)', 'Time-Travel',
                            'Available Time(UTC)', 'Last Modified(UTC)'])
            wks.format('A1:H1', {'textFormat': {'bold': True}})
        wks.append_row(new_data)
        wks.format('A:H', {"horizontalAlignment": "CENTER"})

        color, red_text = format_color(details['status'],
                                 details['can_time_travel'])
        # Headers don't count as data.
        # And we've insert a new row, so move 2 by the length.
        row = len(all_data) + 2
        data_range = 'A{}:H{}'.format(row, row)
        # Update color and text format.
        wks.format(data_range, color)
        if red_text:
            wks.format(data_range, red_text)
