import requests


API_URL = 'https://api3.binance.com/api/v3/avgPrice' #?

# func#1: price request
def get_price(coin: str) -> float:
   """
   :param coin: token name, e.g. BTC for Bitcoin, LTC for Litecoin
   :return: coin's current price in stable USDT. 1USDT ~ 1$ USA
   """
   data = {'symbol': f'{coin}USDT'}  # e.g. BTCUSDT
   response = requests.get(API_URL, data)
   return float(response.json()['price'])

# func#2: profit calculation
def count_profit(coin: dict, current_price: float) -> float:
   """
   :param coin: e.g.:
        {"amount": 1.4466,
         "buy_price": 200,
         "desired_sell_price": 219,
         "last_prices":  [201.4, 205, 203, 211, 222.2],
         "desired_price_fall":  10}
   :param current_price: coin's current price in stable USDT. 1USDT ~ 1$ USA
   :return: profit in USDT
   """
   # Example: (220 - 200) * 0.5 == 10
   return round((current_price - coin['last_enter_price']) * coin['amount'], 2)

# func#3: determines the price fall from the previous peak
def count_price_fall(coin: dict, current_price: float) -> float:
   """
   :param coin: same as in count_profit()
   :param current_price: same as in count_profit()
   :return: max diff between last 5 prices and current price, in USDT
   """
   # Example: max([201.4, 205, 203, 211, 222.2]) - 190 == 32.2
   try:
       return max(coin['last_prices']) - current_price
   except:
       # may happens if coin['last_prices'] is empty
       return 0

# func#4: gives a signal to trade if the price fell by a given percentage
def should_i_buy(price_fall: float, desired_fall: float, current_price: float) -> bool:
   """
   :param price_fall: output of count_price_fall()
   :param desired_fall: desired price fall in PERCENTS! not in USDT. e.g. 10%
   :param current_price: coin's current price in stable USDT
   :return: True if you should buy, False otherwise
   """
   # Example: 21 / 200 * 100 == 10.5% and 10.5 >= 10, so -> True
   if price_fall / current_price * 100 >= desired_fall:
       return True
   return False
# func#5: Check to open a new order
def сheck_open_trades(coin: str, init_depo: float, response: list, state: list) -> bool:
   """
   :param coin: token name, e.g. BTC for Bitcoin, LTC for Litecoin
   :return: coin's current price in stable USDT. 1USDT ~ 1$ USA
   """
   res=True # temporary variable in case the asset is not yet on the balance 
   #response = client.get_open_orders(data)
   if response==[] : # checking the absence of open orders
      #state=client.account(recvWindow=6000)['balances'] # getting the current balance list
      for i in range(len(state)):
         if state[i]['asset']==coin:
            res=False
            if float(state[i]['free'])-init_depo<=0 and float(state[i]['locked'])==0:
               return True
               # break
   else: return False
   return res
def check_asset(coin: str, init_depo: float, state: list) -> dict:
   #state=client.account(recvWindow=6000)['balances'] # getting the current balance list
   d=dict()
   d['free']=0
   d['locked']=0
   for i in range(len(state)):
      if state[i]['asset']==coin:
         free=round(float(state[i]['free'])-init_depo,5)
         locked=round(float(state[i]['locked']),5)
         d['free']=free
         d['locked']=locked
         if (free>0 and locked>0) or free>0 or locked>0:
            return d
         else: break
   return d
#------------------------------------------------------------------------------
def last_stop_loss( get_data: list) -> float:
   # get a call to the open orders method and return a list with a stop price
   res=0
   if get_data==[]:
      return 0
   else:
      for i in range(len(get_data)):
         if get_data[i]['type']=='STOP_LOSS_LIMIT':
            res=round(float(get_data[i]['stopPrice']),5)
            if res>0:
               return res
            else: break
   return res
