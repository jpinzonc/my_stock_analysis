from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd

import os 
# Load libraries 
## Raw Packages
import numpy as np
from math import pi
# from pandas_datareader import data as pdr
import datetime, time
## Data Source
from yahoo_fin import stock_info as si 
## Data Visualization 
from bokeh.plotting import figure, output_file, show, output_notebook
from bokeh.layouts import column, row
# Site Scrapping
import requests
import json
import urllib.request
import statistics
from models.data import *
from models.plots import *
import sqlite3


from bokeh.plotting import figure, output_file, show, output_notebook
from bokeh.layouts import column, row
from bokeh.embed import components, file_html


# current_time = datetime.datetime.now()
# os.environ["NOW"] = current_time.strftime('%m/%d/%Y/%H%M%S')

format_date = '%m/%d/%Y'
current_time = datetime.datetime.now()
os.environ["NOW"] = current_time.strftime(format_date)

app = Flask(__name__)

@app.route("/")
def index():
    # print(datetime.datetime.strptime(os.getenv('NOW'), format_date) - current_time == datetime.timedelta(days=-1))
    now_env = os.getenv('NOW')
    now_dt = datetime.datetime.strptime(now_env, format_date)
    time_diff = now_dt - current_time
    print(time_diff.days==datetime.timedelta(days=-1).days)
    # print(time_diff == datetime.timedelta(days=1).days)
    if time_diff.days != datetime.timedelta(days=-1).days:
        get_data()
    return render_template("index.html")

@app.route("/stock", methods=["POST"])
def stock():
    ticker = request.form["ticker"]
    conn = sqlite3.connect("./static/stock_data.db")
    data = pd.read_sql('SELECT * FROM stocks', conn)
    data = data[data.SYMBOL==ticker.upper()]
    if ticker.upper() not in data.SYMBOL.unique(): 
        return render_template("error.html")

    data.drop(['LASTSALE', 'NETCHANGE', 'PCTCHANGE'], axis = 1, inplace = True)
    indexdata = pd.read_sql('SELECT * FROM index_returns', conn)
    average = indexdata.mean(axis=1).values[0]
    stock_2yrs, returns_multiples, rs_df = ticker_hist(data[data.SYMBOL.str.contains(ticker, case = False)].SYMBOL.unique(), average)
    mdffinal = data[data.SYMBOL.isin(stock_2yrs.SYMBOL.unique())].merge(minervini_check(rs_df, stock_2yrs), on = 'SYMBOL', how = 'left')
    credentials = get_credentials()
    recomd = get_tickers_information(credentials, ['GOOGL', 'DGLY', ticker], get_quote).drop_duplicates()
    data = mdffinal.merge(recomd, on = 'SYMBOL', how = 'left')
    data = data.to_html(index = False)

    stock_data = yf.Ticker(ticker)
    hist = stock_data.history(period="1d")
    hist = hist.to_html(index = False)
    current_v = si.get_live_price(ticker)

    dfd = yf.download(tickers = ticker, period = '1d', interval = '1m').reset_index()
    dfd.columns = dfd.columns.get_level_values(0) 
    dfd["Date"] = pd.to_datetime(dfd["Datetime"]).dt.date
    dfd["Time"] = pd.to_datetime(dfd["Datetime"]).dt.time
    # Previous day data 
    dfpday = yf.download(tickers = ticker, period = '1d', interval = '1d').reset_index().rename(columns = {'index':'Datetime'}) 
    dfpday.columns = dfpday.columns.get_level_values(0) 
    dfpday["Date"] = pd.to_datetime(dfpday["Date"]).dt.date
    # Weekly data 
    dfw = yf.download(tickers = ticker, period ='5d', interval ='1d').reset_index() 
    dfw.columns = dfw.columns.get_level_values(0) 
    dfw = dfw.merge(pd.DataFrame({'Date':pd.date_range(start = dfw.Date.min().strftime('%Y%m%d'), end = dfw.Date.max().strftime('%Y%m%d'), 
                        freq = '1D')}), on = 'Date', how = 'outer').sort_values(by = 'Date').ffill()
    dfw["Weekday"] = pd.to_datetime(dfw["Date"]).dt.day_name()
    # Last Year
    dfy = yf.download(tickers = ticker, period = '5y', interval = '1mo').reset_index() 
    dfy.columns = dfy.columns.get_level_values(0) 
    dfy = dfy[dfy.Date <= dfy.Date.max().replace(day=1)]

    f1 = stockplot(ticker, dfd, "Time", 'd')
    f2 = stockplot(ticker, dfpday, "Date", 'pd')
    f3 = stockplot(ticker, dfw, "Date", 'w')
    f4 = stockplot(ticker, dfy, "Date", 'y')
    plot = column(row(f1, f2), row(f3, f4))
    script = components(plot) 
    script, div = components(plot)

    script1, div1= components(f1)
    script2, div2= components(f2)
    script3, div3= components(f3)
    script4, div4= components(f4)

    return render_template("stock.html", 
                           ticker=ticker, 
                           hist=hist, 
                           data= data,
                           script = script,
                           div=div,
                           current_v = current_v, 
                           script1 = script1, 
                           div1 = div1,
                           div2 = div2,
                           div3 = div3,
                           div4 = div4,
                           script2 = script2,
                           script3 = script3,
                           script4 = script4,
                           )

@app.route("/ticker_list", methods=['GET', "POST"])
def get_data():
    # ft100 = si.tickers_ftse100()
    ft100= pd.read_html("https://en.wikipedia.org/wiki/FTSE_100_Index", attrs = {"id": "constituents"})[0].Ticker.unique()

    ft100 = [i.replace(r'.', '-') for i in ft100]
    # ft250 = si.tickers_ftse250()
    ft250 = pd.read_html("https://en.wikipedia.org/wiki/FTSE_250_Index", attrs = {"id": "constituents"})[0].Ticker.unique()

    ft250 = [i.replace(r'.', '-') for i in ft250]
    ibo = si.tickers_ibovespa()
    ibo = [i.replace(r'.', '-') for i in ibo]
    n50 = si.tickers_nifty50()
    n50 = [i.replace(r'.', '-') for i in n50]
    nfb = si.tickers_niftybank()
    nfb = [i.replace(r'.', '-') for i in nfb]
    nas = si.tickers_nasdaq()
    nas = [i.replace(r'.', '-') for i in nas]
    dow = si.tickers_dow()
    dow = [i.replace(r'.', '-') for i in dow]
    othr = si.tickers_other()
    othr = [i.replace(r'.', '-') for i in othr]
    sp500 = si.tickers_sp500()
    sp500 = [i.replace(r'.', '-') for i in sp500]
    all_yh_tic = {'ft100':ft100, 'ft250': ft250, 'ibo':ibo, 'n50':n50, 'nfb':nfb, 'nas':nas, 'dow':dow, 'other':othr, 'sp500': sp500}

    for key, value in all_yh_tic.items():
        print(key, '\t', len(value))
        
    distinct_tickers = list(set(sp500) | set(dow)| set(nas)|set(othr)|set(ft100)| set(ft250)|set(ibo)|set(n50)|set(nfb))
    print('Total Distinct Tickers',len(distinct_tickers))

    # Collect ingformation from NASDAQ 
    nasdaq = get_nasdaqapi()
    all_stocks = get_quote(distinct_tickers, get_credentials())

    stock_df = pd.DataFrame()
    stocks_sp = np.array_split(all_stocks, 20)
    for i, sp in enumerate(stocks_sp):
        for num, st in enumerate(sp):
            try: 
                dictio = {}
                Symbol = st['symbol']
                dictio['Symbol'] = Symbol
                try:
                    dictio['name'] = st['shortName']
                except: 
                    dictio['name'] = st['longName']
                    
                dictio['lastsale'] = np.round(st['regularMarketPrice'], 2)
                dictio['netchange'] = np.round(st['regularMarketChange'], 2)
                dictio['pctchange'] = np.round(st['regularMarketChangePercent'], 4)
                dictio['last_price'] = np.round(st['regularMarketPrice'], 2)
                dictio['pchange'] = np.round(st['regularMarketChangePercent'], 4)
                temp_df = pd.DataFrame(dictio, index = [0])
                stock_df = pd.concat([stock_df, temp_df]).drop_duplicates(subset = ['Symbol'])
            except: 
                pass
    stock_df.reset_index(drop = True, inplace=True)
    stock_df.columns = [col.upper() for col in stock_df.columns]

    add_info = pd.read_csv('./static/ticker_sectors.csv')
    stocks = stock_df.merge(add_info.rename(columns = {'WEBSITE':'URL'}), how = 'left', on = 'SYMBOL')[nasdaq.drop(['MARKETCAP', 'IPOYEAR', 'VOLUME'], axis = 1).columns].dropna(subset = ['SYMBOL'])

        ### Add exchanges names to the stocks dataframe
    keys = []
    for key, value in all_yh_tic.items():
        keys.append(key)
        stocks.loc[:,key] = np.where(stocks.SYMBOL.isin(value), 1, 0)
        print(key, stocks.shape)
    stocks.loc[:,'NUM_EXCHANGES'] = stocks[keys].sum(1)
    # Calculating the retunr for the indexes - 
    # List of indexes = https://finance.yahoo.com/markets/world-indices/
    _, sp500_return = hist_checker('^GSPC')
    _, dow_return = hist_checker('^DJI')

    conn = sqlite3.connect("./static/stock_data.db")
    stocks.to_sql('stocks', conn, if_exists='replace', index=False)
    pd.DataFrame([[dow_return, sp500_return]], columns= ['dow_return', 'sp500_return']).to_sql('index_returns', conn, if_exists='replace', index=False) 

    return render_template("ticker_list.html", distinct_tickers=distinct_tickers, all_stocks = all_stocks, stock_df = stocks)

@app.route("/bokeh", methods=['GET', "POST"])
def plot():
    language = [ 
        'Python', 'Java', 'JavaScript', 'C#', 'PHP', 'C/C++', 
        'R', 'Objective-C', 'Swift', 'TypeScript', 'Matlab', 
        'Kotlin', 'Go', 'Ruby', 'VBA'
    ] 
    popularity = [ 
        31.56, 16.4, 8.38, 6.5, 5.85, 5.8, 4.08, 2.79, 2.35, 
        1.92, 1.65, 1.61, 1.44, 1.22, 1.16
    ] 
  
    # # Creating Plot Figure 
    # p = figure( 
    #     x_range=language, 
    #     height=400, 
    #     title="Popularity of Programming Languages", 
    #     sizing_mode="stretch_width"
    # ) 
  
    # # Defining Plot to be a Vertical Bar Plot 
    # p.vbar(x=language, top=popularity, width=0.5) 
    # p.xgrid.grid_line_color = None
    # p.y_range.start = 0
  
    # # Get Chart Components 
    # script, div = components(p) 
  
        # Return the components to the HTML template 
    from bokeh.plotting import figure, show
    from bokeh.models import HoverTool
    from bokeh.plotting import figure, show
    from bokeh.models import HoverTool, ColumnDataSource

    # Create some sample data
    
    # Create some sample data
    x = [1, 2, 3]
    y1 = [10, 20, 30]
    y2 = [15, 25, 35]

    # Create a ColumnDataSource
    source = ColumnDataSource(data=dict(x=x, y1=y1, y2=y2))

    # Create a figure
    p = figure(title="Tooltips with Segment and VBar")

    # Add a segment glyph
    p.segment(x0='x', y0='y1', x1='x', y1='y2', color="blue", source=source)

    # Add a vbar glyph
    p.vbar(x='x', top='y2', width=0.5, color="red", source=source)

    # Create a hover tool
    hover = HoverTool(tooltips=[
        ("X", "@x"),
        ("Y1", "@y1"),
        ("Y2", "@y2"),
    ])

    # Add the hover tool to the plot
    p.add_tools(hover)

    # Show the plot
    script, div = components(p) 





    return render_template( 
        template_name_or_list='bokeh.html', 
        script=script, 
        div=div, 
    ) 



if __name__ == "__main__":
    app.run(debug=True, port = 8080)