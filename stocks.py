# author: Waqar Saleem

''' Acknowledgements
- access Google sheet: https://developers.google.com/sheets/api/quickstart/python
- matplotlib legend outside axes: https://stackoverflow.com/questions/4700614/how-to-put-the-legend-out-of-the-plot/43439132#43439132
'''

# Interactive selection in plots from
# - http://matplotlib.org/examples/event_handling/legend_picking.html
# - http://matplotlib.org/examples/widgets/check_buttons.html


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
import datetime as dt

import bisect

class Stock(object):
    def __init__(self, code):
        self.code = code
        self.prices = None
        self.cost_price = 0
        self.name = self.sector = ""
        self.buy_dates, self.buy_rates = [], []
        self.sell_dates, self.sell_rates = [], []
        
class StockPlot(object):
    def __init__(self, code):
        self.code = code
        self.plot_line = self.legend_line = None
        self.buy_line = self.sell_line = self.cost_line = None
        self.is_removed = False
        
    def toggle(self):
        if self.is_removed:
            self.add()
        else:
            self.remove()
            
    def remove(self):
        if self.is_removed:
            return
        for l in [self.plot_line, self.cost_line, self.buy_line,
                  self.sell_line]:
            l.remove()
        self.legend_line.set_alpha(0.2)
        self.is_removed = True

    def add(self):
        if not self.is_removed:
            return
        ax = plt.gca()
        lines = [self.plot_line, self.cost_line, self.buy_line,
                 self.sell_line]
        for i in range(len(lines)):
            lines[i] = ax.add_line(lines[i])
        self.legend_line.set_alpha(1.0)
        self.is_removed = False
        
def get_gsheet_data_offline():
    s = open('offline_data.txt').read()
    return eval(s)

def get_gsheet_data():
    '''get_gsheet_data() -> (list, list, list)

    Returns data from Google sheet as nested lists. The inner list in
    each member list is a row in the sheet. Returns None if no data is
    retrieved from the Google sheet.
    '''
    # Google spreadsheet information.
    scopes = 'https://www.googleapis.com/auth/spreadsheets.readonly'
    spreadsheet_ID = '1oETKmeOHASnIJL06zQIfdzcM3m4zC6j6vk8C4TkpMGQ'
    # Connect to sheet.
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', scopes)
        creds = tools.run_flow(flow, store)
    service = build('sheets', 'v4', http=creds.authorize(Http()))
    # Call the Sheets API
    range_names = ['Portfolio!A:H', 'Trades!A:I', 'Prices!A:ZZ', 'Details!A:ZZ']
    lst = []
    for range_name in range_names:
        result = service.spreadsheets().values()
        result = result.get(spreadsheetId=spreadsheet_ID,
                            range=range_name).execute()
        values = result.get('values', [])
        if not values:
            continue
        lst.append(values)
    return lst

def get_data():
    '''get_data() -> ([dateteime.dateteime], np.ndarray, np.ndarray)

    Returns numpy arrays (dates, prices, headers). dates is a list of
    dates, prices is a corresponding 2D array of floats to be plotted
    against dates, headers is a 1D array for the legend.
    '''
    print("Getting data from Google sheet...", flush=True, end="")
    lst = get_gsheet_data()
    if len(lst) < 4:
        print("Incomplete data received.")
        return
    print("done")
    portfolio, trades, prices, details = [np.array(l) for l in lst]
    code_stock = get_stocks(portfolio)
    dates = get_dates(prices)
    add_price_history(prices, code_stock)
    add_names(details, code_stock)
    add_trade_info(trades, code_stock)
    # Return dates and Stock objects.
    return dates, code_stock

def get_stocks(portfolio):
    # Create Stock objects using code, cost, and sector information
    # from portfolio.
    code_col_index = np.nonzero(portfolio[0]=="Code")[0][0]
    blank_row_index = np.nonzero(portfolio[:,code_col_index]=="")[0][0]
    portfolio = portfolio[:blank_row_index]
    cost_col_index = np.nonzero(portfolio[0]=="Cost Rate")[0][0]
    sector_col_index = np.nonzero(portfolio[0]=="Sector")[0][0]
    indexes = [code_col_index, cost_col_index, sector_col_index]
    code_stock = {}
    for code, cost, sector in portfolio[1:,indexes]:
        stock = Stock(code)
        stock.cost_price = float(cost)
        stock.sector = sector
        code_stock[code] = stock
    return code_stock

def get_dates(prices):
    # Extract dates.
    date_format = "%d-%b-%Y"
    dates = [dt.datetime.strptime(d, date_format) for d in prices[1:,0]]
    # dates = np.array([date2num(d) for d in dates])
    return np.array(dates)

def add_price_history(prices, code_stock):
    # Add price history to Stock objects.
    num_codes = len(prices[0])
    for code_idx in range(1,num_codes):
        column = prices[:,code_idx]
        stock = code_stock[column[0]]
        stock.prices = column[1:].astype(float)

def add_names(details, code_stock):
    # Add name to Stock objects.
    code_col_index = np.nonzero(details[0]=="Code")[0][0]
    name_col_index = np.nonzero(details[0]=="Name")[0][0]
    indexes = [code_col_index, name_col_index]
    for code, name in details[1:,indexes]:
        stock = code_stock[code]
        stock.name = name
        
def add_trade_info(trades, code_stock):
    # Add trade information to Stock objects.
    # Get relevant colums.
    index = np.nonzero(trades[0]=="Date")[0][0]
    df = "%d-%b-%Y"
    dates = [dt.datetime.strptime(d, df) for d in trades[1:,index]]
    index = np.nonzero(trades[0]=="Code")[0][0]
    codes = trades[1:,index]
    index = np.nonzero(trades[0]=="Rate")[0][0]
    rates = trades[1:,index].astype(float)
    index = np.nonzero(trades[0]=="Bought")[0][0]
    bought = trades[1:,index].astype(int)
    # Store buy/sell information from columns in Stock objects.
    for code,stock in code_stock.items():
        buy, sell = [], []
        rows = np.nonzero(codes==code)[0]
        for row in rows:
            qty = bought[row]
            item = (dates[row], rates[row])
            if qty > 0:
                buy.append(item)
            else:
                sell.append(item)
        if buy:
            stock.buy_dates, stock.buy_rates = zip(*buy)
        if sell:
            stock.sell_dates, stock.sell_rates = zip(*sell)
            
def plot_data(dates, code_stock):
    # Plot the data
    ax = plt.gca()
    code_stockplot = {}
    for code, stock in sorted(code_stock.items()):
        stock = code_stock[code]
        stockplot = StockPlot(code)
        line, = ax.plot_date(dates, stock.prices, label=code,
                             linestyle='solid', marker='None', picker=5)
        stockplot.plot_line = line
        color=line.get_color()
        line, = ax.plot_date(stock.buy_dates, stock.buy_rates,
                             marker='o', markersize = 5, color=color)
        stockplot.buy_line = line
        line, = ax.plot_date(stock.sell_dates, stock.sell_rates,
                             marker='s', markersize = 5, color=color)
        stockplot.sell_line = line
        line = ax.axhline(y=stock.cost_price, color=color, alpha = 0.7)
        stockplot.cost_line = line
        code_stockplot[code] = stockplot
    # Format dates on x-axis.
    rule = rrulewrapper(MONTHLY, interval=2)
    loc = RRuleLocator(rule)
    date_format = "%d-%b-%y"
    formatter = DateFormatter(date_format)
    ax.xaxis.set_major_locator(loc)
    ax.xaxis.set_major_formatter(formatter)
    ax.xaxis.set_tick_params(rotation=30,labelsize=10)
    # Other settings - tight axes, grid, title.
    ax.set_xlim(dates[0], dates[-1])
    ax.grid(b=True, axis='y')
    ax.set_title('Stock Price History')
    return code_stockplot

class SnaptoCursors(object):
    def __init__(self, ax, x, ys):
        self.ax = ax
        self.x = np.array([date2num(d) for d in x])
        self.ys = ys
        self.ly = ax.axvline(color='k', alpha=0.2)  # the vert line
        self.size = len(ys[0])
        self.colors = [l.get_color() for l in ax.get_lines()]
        self.txt = ax.figure.text(0.6, 0.9, 'Hello World', fontsize=8)
        xs = [x[-1]]*self.size
        ys = ys[-1,:]
        self.markers = ax.scatter(xs, ys, marker="o", color=self.colors, zorder=3)

    def mouse_move(self, event):
        if not event.inaxes:
            return
        x, y = event.xdata, event.ydata
        indx = bisect.bisect(self.x, x)
        if indx >= len(self.x):
            return
        x = self.x[indx]
        self.ly.set_xdata(x)
        ys = self.ys[indx,:]
        self.markers.remove()
        self.markers = self.ax.scatter([x]*self.size, ys, marker="o", color=self.colors, zorder=3)
        self.txt.set_text("Move {}, {}".format(event.xdata, event.ydata))
        # self.markers.set_data([x]*self.size, ys)
        # for m,y in zip(self.markers,ys):
        #     m.set_data([x],[y])
        self.ax.figure.canvas.draw_idle()

def make_and_connect_legend(code_stockplot):
    '''make_and_connect_legend() -> dict

    Retuns a mapping from legend lines to plotted lines. The legend is
    set as per headers.
    '''
    ax = plt.gca()
    # Place legend to the right of axes and adjust plot size.
    legend = ax.legend(fancybox=True, shadow=True, loc='center left', bbox_to_anchor=(1, 0.5))
    plt.subplots_adjust(right=0.8)
    # Make legend lines pickable. Map each legend line to its plot line.
    plot_lines = ax.get_lines()
    legend_lines = legend.get_lines()
    _, legend_labels = ax.get_legend_handles_labels()
    for code,line in zip(legend_labels,legend_lines):
        line.set_picker(5)  # 5 pts tolerance
        code_stockplot[code].legend_line = line

def enable_hiding(code_stockplot):
    '''enable_hiding(dict) -> None

    Uses the mapping in legend_to_plot from legend line to plot line
    to enable interactive hiding of plot lines.
    '''
    fig = plt.gcf()
    ax = plt.gca()
    def onpick(event):
        # when legend line is picked, toggle the visibility of the
        # corresponding plot line
        legend_line = event.artist
        code = legend_line.get_label()
        code_stockplot[code].toggle()
        # recompute the ax.dataLim
        ax.relim()
        # update ax.viewLim using the new dataLim
        # ax.autoscale_view(scalex=False)
        ax.autoscale()
        fig.canvas.draw_idle()
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
    dates, code_stock = data
    # Prepare plot.
    plt.subplots()  # initialize plot
    code_stockplot = plot_data(dates, code_stock)
    make_and_connect_legend(code_stockplot)
    # cursors = SnaptoCursors(plt.gca(), dates, prices)
    # plt.connect('motion_notify_event', cursors.mouse_move)
    # Add handlers.
    enable_hiding(code_stockplot)
    # Show plot.    
    plt.show()

if __name__ == '__main__':
    main()
