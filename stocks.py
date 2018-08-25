# author: Waqar Saleem

# Google sheet access code from https://developers.google.com/sheets/api/quickstart/python

# To access Google Sheets
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

# For plotting
import matplotlib.pyplot as plt
from matplotlib.dates import (MONTHLY, DateFormatter,
                              rrulewrapper, RRuleLocator,
                              num2date, date2num)
from matplotlib.widgets import CheckButtons

import numpy as np
import datetime

import bisect

# from snaptocursor import SnaptoCursors

## Google spreadsheet information.
# If modifying these scopes, delete the file token.json.
SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
# The ID and range of a sample spreadsheet.
SPREADSHEET_ID = '1oETKmeOHASnIJL06zQIfdzcM3m4zC6j6vk8C4TkpMGQ'
RANGE_NAME = 'Prices!A:J'

DATE_FORMAT = "%d-%b-%Y"


class SnaptoCursors(object):
    def __init__(self, ax, x, ys):
        self.ax = ax
        right = x[-1]
        bottom = ys[0,0]
        self.ly = ax.axvline(color='k', alpha=0.2)  # the vert line
        self.marker, = ax.plot([right],[bottom], marker="o", color="crimson", zorder=3, linestyle='None', markersize=2)
        self.x = np.array([date2num(d) for d in x])
        self.ys = ys

    def mouse_move(self, event):
        if not event.inaxes:
            return
        x, y = event.xdata, event.ydata
        indx = bisect.bisect(self.x, x)
        if indx >= len(self.x):
            return
        x = self.x[indx]
        ys = self.ys[indx,:]
        self.ly.set_xdata(x)
        self.marker.set_data([x],ys)
        self.ax.figure.canvas.draw_idle()

def get_gsheet_data_offline():
    s = open('offline_data.txt').read()
    return eval(s)

def get_gsheet_data():
    '''get_gsheet_data() -> list

    Returns data from Google sheet as a nested list. Each inner list
    is a row in the sheet. Returns None if no data is retrieved from
    the Google sheet.
    '''
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('sheets', 'v4', http=creds.authorize(Http()))
    # Call the Sheets API
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID,
                                                range=RANGE_NAME).execute()
    values = result.get('values', [])
    return values

def get_data():
    '''get_data() -> ([dateteime.dateteime], np.ndarray, np.ndarray)

    Returns numpy arrays (dates, prices, headers). dates is a list of
    dates, prices is a corresponding 2D array of floats to be plotted
    against dates, headers is a 1D array for the legend.
    '''
    print("Getting data from Google sheet...", flush=True, end="")
    values = get_gsheet_data_offline()  # 2D list
    print("done")
    if not values:
        print("No data received.")
        return
    values = np.array(values)
    headers = values[0, 1:]
    dates = np.array(values[1:,0])
    dates = [datetime.datetime.strptime(d, DATE_FORMAT) for d in dates]
    # dates = np.array(values[1:,0], dtype=datetime.date)
    prices = np.array(values[1:,1:], dtype=float)
    return (dates, prices, headers)

def plot_data(dates, prices):
    '''plot_date([datetime.datetime], np.ndarray) -> None

    Plots prices against dates and does necessary formatting.
    '''
    # Plot the data
    ax = plt.gca()
    lines = ax.plot_date(dates, prices, linestyle='solid', marker='None', picker=5)
    # Format dates on x-axis.
    rule = rrulewrapper(MONTHLY, interval=2)
    loc = RRuleLocator(rule)
    formatter = DateFormatter(DATE_FORMAT)
    ax.xaxis.set_major_locator(loc)
    ax.xaxis.set_major_formatter(formatter)
    ax.xaxis.set_tick_params(rotation=30,labelsize=10)
    # Snap axis to data.
    ax.set_xlim(dates[0], dates[-1])
    # Other settings - grid, title.
    ax.grid(b=True, axis='y')
    ax.set_title('Latest Stock Data')

def make_and_connect_legend(headers):
    '''make_and_connect_legend(np.ndarry) -> dict

    Retuns a mapping from legend lines to plotted lines. The legend is
    set as per headers.
    '''
    ax = plt.gca()
    legend = ax.legend(headers, fancybox=True, shadow=True)
    
    plot_lines = ax.get_lines()
    legend_lines = legend.get_lines()
    for line in legend_lines:
        line.set_picker(5)  # 5 pts tolerance
    return dict(zip(legend_lines, plot_lines))

def enable_hiding(legend_to_plot):
    '''enable_hiding(dict) -> None

    Uses the mapping in legend_to_plot from legend line to plot line
    to enable interactive hiding of plot lines.
    '''
    fig = plt.gcf()
    def onpick(event):
        # when legend line is picked, toggle the visibility of the
        # corresponding plot line
        legend_line = event.artist
        plot_line = legend_to_plot[legend_line]
        vis = not plot_line.get_visible()
        plot_line.set_visible(vis)
        # Change the alpha on the line in the legend so we can see
        # what lines have been toggled
        if vis:
            legend_line.set_alpha(1.0)
        else:
            legend_line.set_alpha(0.2)
        fig.canvas.draw()
    fig.canvas.mpl_connect('pick_event', onpick)

# def enable_hover():
#     '''enable_hover(None) -> None

#     Adds hover effects.
#     '''
#     fig = plt.gcf()
#     def onhover(event):
#         if event.inaxes:
#             print('x,y,xdata,ydata: {}, {}, {}, {}'.format(event.x,event.y,num2date(event.xdata).date(),event.ydata))
#             # fig.canvas.draw_cursor(event)
#     fig.canvas.mpl_connect('motion_notify_event', onhover)

def main():
    # Get data from Google sheet.
    data = get_data()
    if not data:
        return
    dates, prices, headers = data
    # Prepare plot.
    plt.subplots()  # initialize plot
    plot_data(dates, prices)
    legend_to_plot = make_and_connect_legend(headers)
    cursors = SnaptoCursors(plt.gca(), dates, prices)
    plt.connect('motion_notify_event', cursors.mouse_move)
    # Add handlers.
    enable_hiding(legend_to_plot)
    # Show plot.    
    plt.show()

if __name__ == '__main__':
    main()
