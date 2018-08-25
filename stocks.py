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
                              num2date)
from matplotlib.widgets import CheckButtons

import numpy as np
import datetime

## Google spreadsheet information.
# If modifying these scopes, delete the file token.json.
SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
# The ID and range of a sample spreadsheet.
SPREADSHEET_ID = '1oETKmeOHASnIJL06zQIfdzcM3m4zC6j6vk8C4TkpMGQ'
RANGE_NAME = 'Prices!A:J'

DATE_FORMAT = "%d-%b-%Y"

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
    plt.gcf().canvas.mpl_connect('pick_event', onpick)

def enable_hover():
    '''enable_hover(None) -> None

    Adds hover effects.
    '''
    fig = plt.gcf()
    def onhover(event):
        if event.inaxes:
            print('x,y,xdata,ydata: {}, {}, {}, {}'.format(event.x,event.y,num2date(event.xdata).date(),event.ydata))
            fig.canvas.draw_cursor(event)
    fig.canvas.mpl_connect('motion_notify_event', onhover)

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
    # Add handlers.
    enable_hiding(legend_to_plot)
    enable_hover()
    # Show plot.    
    plt.show()

    
# def check_buttons():
#     t = np.arange(0.0, 2.0, 0.01)
#     s0 = np.sin(2*np.pi*t)
#     s1 = np.sin(4*np.pi*t)
#     s2 = np.sin(6*np.pi*t)

#     fig, ax = plt.subplots()
#     l0, = ax.plot(t, s0, visible=False, lw=2)
#     l1, = ax.plot(t, s1, lw=2)
#     l2, = ax.plot(t, s2, lw=2)
#     plt.subplots_adjust(left=0.2)

#     rax = plt.axes([0.05, 0.4, 0.1, 0.15])
#     check = CheckButtons(rax, ('2 Hz', '4 Hz', '6 Hz'), (False, True, True))


#     def func(label):
#         if label == '2 Hz':
#             l0.set_visible(not l0.get_visible())
#         elif label == '4 Hz':
#             l1.set_visible(not l1.get_visible())
#         elif label == '6 Hz':
#             l2.set_visible(not l2.get_visible())
#         plt.draw()
#     check.on_clicked(func)

#     plt.show()    

    
# def event_handling():
#     t = np.arange(0.0, 0.2, 0.1)
#     y1 = 2*np.sin(2*np.pi*t)
#     y2 = 4*np.sin(2*np.pi*2*t)

#     fig, ax = plt.subplots()
#     ax.set_title('Click on legend line to toggle line on/off')
#     line1, = ax.plot(t, y1, lw=2, color='red', label='1 HZ')
#     line2, = ax.plot(t, y2, lw=2, color='blue', label='2 HZ')
#     leg = ax.legend(loc='upper left', fancybox=True, shadow=True)
#     leg.get_frame().set_alpha(0.4)


#     # we will set up a dict mapping legend line to orig line, and enable
#     # picking on the legend line
#     lines = [line1, line2]
#     lined = dict()
#     for legline, origline in zip(leg.get_lines(), lines):
#         legline.set_picker(5)  # 5 pts tolerance
#         lined[legline] = origline

#     def onpick(event):
#         # on the pick event, find the orig line corresponding to the
#         # legend proxy line, and toggle the visibility
#         legline = event.artist
#         origline = lined[legline]
#         vis = not origline.get_visible()
#         origline.set_visible(vis)
#         # Change the alpha on the line in the legend so we can see what lines
#         # have been toggled
#         if vis:
#             legline.set_alpha(1.0)
#         else:
#             legline.set_alpha(0.2)
#         fig.canvas.draw()

#     fig.canvas.mpl_connect('pick_event', onpick)

#     plt.show()    

if __name__ == '__main__':
    main()
