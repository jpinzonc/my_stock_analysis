# Load libraries 
## Raw Packages
import numpy as np
import pandas as pd
from math import pi
# from pandas_datareader import data as pdr
import datetime, time
## Data Source
import yfinance as yf
# To let pdr get data from yahoo -- https://stackoverflow.com/questions/74912452/typeerror-string-indices-must-be-integer-pandas-datareader
# yf.pdr_override()
from yahoo_fin import stock_info as si 
## Data Visualization 
from bokeh.plotting import figure, output_file, show, output_notebook
from bokeh.layouts import column, row
# Site Scrapping
import requests
import json
import urllib.request
 

#########################################################################
# Functions

apiBase = 'https://query2.finance.yahoo.com'
headers = { 
  "User-Agent": 
  "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
}

def get_credentials(cookieUrl='https://fc.yahoo.com', crumbUrl=apiBase+'/v1/test/getcrumb'):
  '''
  https://stackoverflow.com/questions/76065035/yahoo-finance-v7-api-now-requiring-cookies-python
  '''
  cookie = requests.get(cookieUrl).cookies
  crumb = requests.get(url=crumbUrl, cookies=cookie, headers=headers).text
  return {'cookie': cookie, 'crumb': crumb}

def get_quote(symbols, credentials):
  '''
  https://stackoverflow.com/questions/76065035/yahoo-finance-v7-api-now-requiring-cookies-python
  '''
  final_list = []
  try:
    url = apiBase + '/v7/finance/quote'
    symbols_a = np.array_split(symbols, 3)
    for sp in symbols_a:
      params = {'symbols': ','.join(sp), 'crumb': credentials['crumb']}
      response = requests.get(url, params=params, cookies=credentials['cookie'], headers=headers)
      quotes = response.json()['quoteResponse']['result']
      final_list  = final_list + quotes
    return final_list
  except: 
    pass

def info_parser(df, quot, col, element):
      try: 
        df.loc[:, col] = quot[element]
      except: 
        df.loc[:, col] = '' 
      return df 

def get_tickers_information(credentials, tickers, get_quote):
    col_element = {'Price':'regularMarketPrice', 
               'Divident_Yield' : 'dividendYield',
               'Analyst_Recomdtn': 'averageAnalystRating',
               'Divident_Rate' : 'dividendRate'
               }
    quotes = get_quote(tickers, credentials)
    stock_info = pd.DataFrame()
    for quote in quotes:
        try: 
            print(f"{quote['symbol']}") # price is {quote['currency']} {quote['regularMarketPrice']} {quote['dividendYield']}")
            tickerdiv = si.get_dividends(quote['symbol'])
            tickerdiv = tickerdiv[tickerdiv.index == tickerdiv.index.max()].reset_index()
            tickerdiv.rename(columns = {'index':'Dividend_DT', 'ticker':'Symbol', 'dividend':'Dividend_AMT'}, inplace = True)
            for col, element in col_element.items():
                info_parser(tickerdiv, quote, col, element)
            stock_info = pd.concat([stock_info, tickerdiv], axis = 0)
        except Exception as E: 
            print("\t", E)
            continue
    stock_info[['Symbol', 'Price', 'Dividend_AMT', 'Dividend_DT', 'Divident_Yield', 'Divident_Rate', 'Analyst_Recomdtn']].reset_index(drop = True)
    stock_info.columns = [col.upper() for col in stock_info.columns]
    return stock_info



def min_value(value, df, field):
    if value == None:
        value = df[field].min()
    return value

def max_value(value, df, field):
    if value == None:
        value = df[field].max()
    return value

def filter_stocks(df, minprice, maxprice, minpct, maxpct, country):
    if 'RS_Rating' in df.columns:
        df = df[df.RS_Rating.isna()==False]
    return df[(df.LAST_PRICE >= minprice)\
                 &(df.LAST_PRICE <= maxprice)\
                 &(df.PCHANGE >= minpct)\
                 &(df.PCHANGE <= maxpct)\
                 &(df.COUNTRY == country)]\
            .sort_values(by = ['SYMBOL', 'LAST_PRICE', 'PCHANGE'], ascending = [True, False, True])


def get_nasdaqapi(exchange = None):
    '''
    Get the latest value of all stocks FROM Nasdaq.com
    https://github.com/shilewenuw/get_all_tickers/issues/12
    
    Available exchanges: nasdaq, amex, nyse
    '''
    headers = {'authority': 'api.nasdaq.com',
                'accept': 'application/json, text/plain, */*',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36',
                'origin': 'https://www.nasdaq.com',
                'sec-fetch-site': 'same-site',
                'sec-fetch-mode': 'cors',
                'sec-fetch-dest': 'empty',
                'referer': 'https://www.nasdaq.com/',
                'accept-language': 'en-US,en;q=0.9',
                }
    dparams = (('tableonly', 'true'),
                ('limit', '250'),
                ('offset', '0'),
                ('download', 'true')
             )    
    if exchange != None:
        dparams = dparams + (('exchange',exchange),)
    r = requests.get('https://api.nasdaq.com/api/screener/stocks', headers = headers, params = dparams)
    stocksj = r.json()['data']
    stocksdf = pd.DataFrame(stocksj['rows'], columns = stocksj['headers'])
    stocksdf = stocksdf[~stocksdf['symbol'].str.contains(r"\.|\^")]
    # display(stocks.shape)
    # Changing values to numbers in last price and percent change fields. 
    stocksdf.loc[:,'last_price'] = stocksdf.lastsale.str.replace(r'\$', '', regex = True).astype(float)
    stocksdf.loc[:,'pchange'] = stocksdf.pctchange.str.replace(r'\%|\s', '', regex = True)#.astype(float)
    stocksdf.loc[:,'symbol'] = stocksdf.symbol.str.replace(r'\/', '-', regex = True)#.astype(float)

    stocksdf.loc[:,'pchange'] = stocksdf.pchange.str.replace(r'^$', '-999', regex = True).astype(float)
    stocksdf.rename(columns = {'symbol':'Symbol'}, inplace = True)
    stocksdf.loc[:,'Symbol'] = stocksdf['Symbol'].str.strip()
    stocksdf.columns = [col.upper() for col in stocksdf.columns]

    return stocksdf#, stocksj

from pandas_datareader import data
from yfinance.multi import download
from functools import wraps
#https://stackoverflow.com/questions/78561896/installed-correct-version-of-panda-datareader-but-seem-to-be-getting-an-error-wh

def override_yahoo_behavior(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract the data_source parameter from the kwargs
        data_source = kwargs.get("data_source")
        # If data_source is not provided in kwargs, check args
        if data_source is None and len(args) > 1:
            data_source = args[1]
        # Check if the data_source is "yahoo" and return the custom behavior
        if data_source == "yahoo":
            # get the name, start, and end date from the kwargs or args
            name = kwargs.get("name")
            start_date = kwargs.get("start")
            end_date = kwargs.get("end")
            # If not in kwargs, check args
            if name is None and len(args) > 0:
                name = args[0]
            if start_date is None and len(args) > 2:
                start_date = args[2]
            if end_date is None and len(args) > 3:
                end_date = args[3]
            return download(tickers=name, start=start_date, end=end_date)
        # Otherwise, call the original function
        return func(*args, **kwargs)
    return wrapper

def hist_checker(ticker):
    '''
    Captures the history of the symbol provided. 
    It can be a ticker or a symbol like : '^GSPC' for S&P 500
    returns the historical data and the return of the index
    '''
    index_name = ticker# '^GSPC' # S&P 500
    start_datef = datetime.datetime.now() - datetime.timedelta(days=365*2)
    end_datef = datetime.date.today()
    data.DataReader = override_yahoo_behavior(data.DataReader)
    index_df = data.DataReader(index_name, "yahoo", start_datef, end_datef)
    index_df['Percent Change'] = index_df['Adj Close'].pct_change()
    # index_return = (index_df['Percent Change'] + 1).cumprod()[-1]
    index_return = (index_df['Percent Change'] + 1).cumprod().iloc[-1]
    index_df.columns = ['Adj Close', 'Close',	'High',	'Low', 'Open','Volume',	'Percent Change']
    index_df.reset_index(inplace = True)
    index_df.insert(loc=0, column='Symbol', value=ticker)
    index_df.columns = [col.upper() for col in index_df.columns]
    return index_df, index_return

def ticker_hist(tickers_list, pctreturn):
    stock_2yrs = rs_df = pd.DataFrame()
    returns_multiples = []
    data.DataReader = override_yahoo_behavior(data.DataReader)
    for ticker in tickers_list:
        # Download historical data as CSV for each stock (makes the process faster)
        try:
            df, stock_return = hist_checker(ticker)
            # Calculating returns relative to the market (returns multiple)
            returns_multiple = round((stock_return / pctreturn), 2)
            returns_multiples.extend([returns_multiple])
            stock_2yrs = pd.concat([stock_2yrs, df], sort =  False )
            # Creating dataframe of only top 30%
            rs_df = pd.DataFrame(list(zip(tickers_list, returns_multiples)), columns=['SYMBOL', 'RETURNS_MULTIPLE' ])
    #             rs_df['RS_Rating'] = rs_df.Returns_multiple.rank(pct=True) * 100
    #             rs_df = rs_df[rs_df.RS_Rating >= rs_df.RS_Rating.quantile(.70)]#         time.sleep(0.25)
        except Exception as E:
            print('ERROR:' , str(E))
            pass
    return stock_2yrs, returns_multiples, rs_df

def minervini_check(rs_df, stock_2yrs):
    '''
    Checking Minervini conditions of top 30% of stocks in given list
    '''
    minervi_df = pd.DataFrame(columns=['SYMBOL', "50 Day MA", "150 Day Ma", "200 Day MA", "52 Week Low", "52 week High"])
    rs_stocks = rs_df['SYMBOL']
    for stock in rs_stocks: 
        # mdf = pd.DataFrame()#columns=['Symbol', "RS_Rating", "50 Day MA", "150 Day Ma", "200 Day MA", "52 Week Low", "52 week High"])
        # time.sleep(0.5)
        try:
            df = stock_2yrs[stock_2yrs.SYMBOL == stock]#pdr.get_data_yahoo(stock, start_date, end_date)
            sma = [50, 150, 200]
            for x in sma:
                df.loc[:,"SMA_"+str(x)] = round(df['ADJ CLOSE'].rolling(window=x).mean(), 2)
            # Storing required values 
            currentClose = df["ADJ CLOSE"].values[-1]
            moving_average_50 = df["SMA_50"].values[-1]
            moving_average_150 = df["SMA_150"].values[-1]
            moving_average_200 = df["SMA_200"].values[-1]
            low_of_52week = round(min(df["LOW"][-260:]), 2)
            high_of_52week = round(max(df["HIGH"][-260:]), 2)
#             RS_Rating = round(rs_df[rs_df['Symbol']==stock].RS_Rating.tolist()[0])
            try:
                moving_average_200_20 = mean(df["SMA_200"].values[-20:])
            except Exception:
                moving_average_200_20 = 0
            # Condition 1: Current Price > 150 SMA and > 200 SMA
            condition_1 = currentClose > moving_average_150 > moving_average_200   
            # Condition 2: 150 SMA and > 200 SMA
            condition_2 = moving_average_150 > moving_average_200
            # Condition 3: 200 SMA trending up for at least 1 month
            condition_3 = moving_average_200 > moving_average_200_20      
            # Condition 4: 50 SMA> 150 SMA and 50 SMA> 200 SMA
            condition_4 = True if  moving_average_50 > moving_average_150 > moving_average_200 else False         
            # Condition 5: Current Price > 50 SMA
            condition_5 = currentClose > moving_average_50          
            # Condition 6: Current Price is at least 30% above 52 week low
            condition_6 = currentClose >= (1.3*low_of_52week)         
            # Condition 7: Current Price is within 25% of 52 week high
            condition_7 = currentClose >= (.75*high_of_52week)      
            # If all conditions above are true, add stock to exportList
            mdf =pd.DataFrame.from_dict({'SYMBOL': [stock],"50 Day MA": [moving_average_50]
                                            , "150 Day Ma": [moving_average_150], "200 Day MA": [moving_average_200]
                                            , "52 Week Low": [low_of_52week], "52 week High": [high_of_52week]}
                                           )
            if condition_1 : #and condition_2 and condition_3 and condition_4 and condition_5 and condition_6 and condition_7:
                mdf.loc[:,'minervis'] = 'Yes'
                print (stock + " fulfills Minervini's requirements")
            else: 
                mdf.loc[:,'minervis'] = 'No'
                print("{} does NOT fulfill Minervini's requirements".format(stock))
            minervi_df = minervi_df.dropna(axis=1, how='all')
            mdf = mdf.dropna(axis=1, how='all')
            minervi_df = pd.concat([minervi_df, mdf], axis = 0)
            
        except Exception as e:
            print (str(e))
            print(f"Could not gather data on {stock}")
            return
    minervi_df.columns = [col.upper() for col in minervi_df.columns]
    return minervi_df

def get_tickers_most_recent_divident(tickers):
    stock_info = pd.DataFrame()
    for ticker in tickers:
        try: 
            tickerdiv = si.get_dividends(ticker)
            tickerdiv = tickerdiv[tickerdiv.index == tickerdiv.index.max()].reset_index()
            tickerdiv.rename(columns = {'index':'Dividend_DT', 'ticker':'Symbol', 'dividend':'Dividend_AMT'}, inplace = True)
            stock_info = pd.concat([stock_info, tickerdiv], axis = 0)
        except Exception as E: 
            print("\t", E)
            continue
    stock_info.columns = [col.upper() for col in stock_info.columns]
    return stock_info.reset_index(drop = True)