#!/usr/bin/env python
# coding: utf-8

# In[1]:


import logging
import datetime
import statistics
from time import sleep
from alice_blue import *
import talib 
import websocket
import json
import pandas as pd
import requests, json
import dateutil.parser
from datetime import timedelta, time, date, datetime


# In[2]:


username = "123456"  #Incorrect information used
password ="123456"   #Incorrect information used
twoFA = "1900"       #Incorrect information used
api_secret = "qwertyuio"   #Incorrect information used
app_id= "asdfghjkk"        #Incorrect information used
Stock_List = 'TATAMOTORS' # We can add n number of stocks here as a list


# In[3]:


print (Stock_List)


# In[4]:


ltp = 0
socket_opened = False
alice = None
def event_handler_quote_update(message):
    global ltp
    ltp = message['ltp']

def open_callback():
    global socket_opened
    socket_opened = True

def buy_signal(ins_scrip):
    global alice
    alice.place_order(transaction_type = TransactionType.Buy,
                         instrument = ins_scrip,
                         quantity = 1,
                         order_type = OrderType.Market,
                         product_type = ProductType.Intraday,
                         price = 0.0,
                         trigger_price = None,
                         stop_loss = None,
                         square_off = None,
                         trailing_sl = None,
                         is_amo = False)
def sell_signal(ins_scrip):
    global alice
    alice.place_order(transaction_type = TransactionType.Sell,
                         instrument = ins_scrip,
                         quantity = 1,
                         order_type = OrderType.Market,
                         product_type = ProductType.Intraday,
                         price = 0.0,
                         trigger_price = None,
                         stop_loss = None,
                         square_off = None,
                         trailing_sl = None,
                         is_amo = False)
    


# In[5]:


def main():
    global socket_opened
    global alice
    global username
    global password
    global twoFA
    global api_secret
    global Stock_List
    minute_close = []
    access_token = AliceBlue.login_and_get_access_token(username=username, 
                                                        password=password, 
                                                        twoFA=twoFA, 
                                                        api_secret=api_secret, 
                                                        app_id=app_id)

    alice = AliceBlue(username=username, 
                      password=password, 
                      access_token=access_token, 
                      master_contracts_to_download=['NSE'])

#   print(alice.get_balance()) # get balance / margin limits
#   print(alice.get_profile()) # get profile
#   print(alice.get_daywise_positions()) # get daywise positions
#   print(alice.get_netwise_positions()) # get netwise positions
#   print(alice.get_holding_positions()) # get holding positions

    ins_scrip = alice.get_instrument_by_symbol('NSE', Stock_List)

    socket_opened = False
    alice.start_websocket(subscribe_callback=event_handler_quote_update,
                          socket_open_callback=open_callback,
                          run_in_background=True)
    while(socket_opened==False):    # wait till socket open & then subscribe
        pass
    alice.subscribe(ins_scrip, LiveFeedType.COMPACT)
    
    instrument = ins_scrip
    from_datetime = datetime.now() - timedelta(days=5)
    to_datetime = datetime.now()
    interval = "5_MIN"   # ["DAY", "1_HR", "3_HR", "1_MIN", "5_MIN", "15_MIN", "60_MIN"]
    indices = False
    
    def get_historical(instrument, from_datetime, to_datetime, interval, indices=False):
        
        
        params = {"token": instrument.token,
                  "exchange": instrument.exchange if not indices else "NSE_INDICES",
                  "starttime": str(int(from_datetime.timestamp())),
                  "endtime": str(int(to_datetime.timestamp())),
                  "candletype": 3 if interval.upper() == "DAY" else (2 if interval.upper().split("_")[1] == "HR" else 1),
                  "data_duration": None if interval.upper() == "DAY" else interval.split("_")[0]}
        lst = requests.get(
            f" https://ant.aliceblueonline.com/api/v1/charts/tdv?", params=params).json()["data"]["candles"]
        records = []
        for i in lst:
            record = {"date": dateutil.parser.parse(i[0]), "open": i[1], "high": i[2], "low": i[3], "close": i[4], "volume": i[5]}
            records.append(record)
        return records


    df = pd.DataFrame(get_historical(instrument, from_datetime, to_datetime, interval, indices))

    df.index = df["date"]
    df = df.drop("date", axis=1)
    #df = df.loc[df.index==datetime.now(),:] # Filetering I have to use to trading time and date

#     df["MA_10"] = df["close"].rolling(window=10).mean()
#     df["MA_20"] = df["close"].rolling(window=20).mean()
#     df["MA_50"] = df["close"].rolling(window=50).mean()
#     df
    
    
    df['MA_10'] = talib.MA(df["close"], timeperiod = 10)
    df['MA_21'] = talib.MA(df["close"], timeperiod = 21)
    df['MA_50'] = talib.MA(df["close"], timeperiod = 50)
    df['RSI_14'] = talib.RSI(df["close"], timeperiod = 14)
#     df['ATR_14'] = talib.ATR(df["ltp"], df["High"],df["Low"], timeperiod = 14)

    current_signal = ''
    list_new = []
    for i in df.index[49:]:
        if df['close'][i] and df['open'][i] > df['MA_50'][i] and df['RSI_14'][i] > 60 and current_signal != "Buy": 
            print (i,"Buy",df['close'][i])
            list_new.append ((i,"Buy",df['close'][i]))
            buy_signal(ins_scrip)
            current_signal = 'Buy'
            
        if df['close'][i] and df['open'][i] < df['MA_50'][i] and df['RSI_14'][i] < 40 and current_signal != "Sell":
            list_new.append((i, "Sell", df['close'][i] )) 
            sell_signal(ins_scrip)
            current_signal = 'Sell'
            
        if df['close'][i] and df['open'][i] < df['MA_50'][i] and current_signal == "Buy":
            list_new.append ((i, "Buy_square_off", df['close'][i] ))
            sell_signal(ins_scrip)
            current_signal = 'square_off'
            
        if df['close'][i] and df['open'][i] > df['MA_50'][i] and current_signal == "Sell":
            list_new.append ((i, "Sell_square_off", df['close'][i]))
            buy_signal(ins_scrip)
            current_signal = 'square_off'
    
        
        sleep(1)
    sleep(0.2)  # sleep for 200ms

    stock_trade = pd.DataFrame(list_new,columns=["Time", "Signal", "Trading_Price"] )
    print(stock_trade)

if(__name__ == '__main__'):
    main()


# In[ ]:





# In[ ]:




