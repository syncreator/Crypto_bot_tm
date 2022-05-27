import time
import json
from urllib import response
from binance.spot import Spot as Client
from telegram.ext import Updater, CommandHandler
from calculations import count_price_fall, should_i_buy, сheck_open_trades, check_asset, last_stop_loss

# Binance_Test Tokens:
api_key="RYTUUIpoiooppxVXmfsvp8w4hV6zxRgNEH8auD7vj3e"#creds.api_key_testnet
sec_key="TiuooTYiOPPoUyRRuyuIptT9BeqfeZ3EGF5WX6lauMj"#creds.sec_key_testnet
# Binance Client create:
client = Client(api_key, sec_key, base_url="https://testnet.binance.vision")

# You Telegram Token:
TOKEN = '55555555555:AAEoi-YD$77990GHhjLnpI_I8JzR4l_ulpyDFk'

# Request of account state func(): 
def req_statement(update, context):
    chat_id = update.effective_chat.id
    message = ['Account:\n']
    ms=''
# Request of account state:    
    state=client.account(recvWindow=6000)['balances']
    for i in range(len(state)):
        for key in state[i]:
            if key=='asset':
                ms+=f'{state[i][key]}->'
            else:
                ms+=f'{key}: {round(float(state[i][key]),5)}; '
        ms+='\n'
    message.append(ms)
# Message result:)
    context.bot.send_message(chat_id=chat_id, text='\n'.join(message))
# -------------------------------------------------------------

def start(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                     text="Hello , Thanks for choosing us!!")

    context.job_queue.run_repeating(callback_minute, interval=20, first=5,
                                    context=update.message.chat_id)

# Main bot func:
#-----------------------------------
def callback_minute(context):
    chat_id=context.job.context
    #--------------------------------
# (открываете файл my_cryptocoins.json и читаете из него данные)
    with open('TM_Trade_Bot\my_cryptocoins.json', 'r') as my_coins_data:
       my_coins = json.loads(my_coins_data.read())

# (эта переменная будет содержать в себе тот сообщение, которое бот вам отправит в Телеграме)
    final_message = []
    ttime = my_coins['time']
# (цикл, проходящий по всем токенам, перечисленным в my_cryptocoins.json)
    for coin_name in my_coins.keys():
       if coin_name=='time':
           continue
       else:
           coin = my_coins[coin_name]
           coin_price = float(client.klines(f'{coin_name}USDT', "1m", limit=1)[0][1])#get_price(coin_name) # Получение текущей цены по текущему coin_name
           price_fall = count_price_fall(coin, coin_price) #вычисление текущей разницы  максимального значения цены из массива и текущей ценой.
           last_prices = coin['last_prices'] #текущий массив цен last_prices
    
# (часть кода, отвечающая за работу с ценами, обновляемыми каждую минуту)
           t_now = time.time()
           if t_now - ttime[0]>=60.0 : # check timeout 60 seconds
               my_coins['time'] = [t_now]
               if len(last_prices) <= 60:
                   last_prices.append(coin_price)
                   if len(last_prices) <= 59:
                       price_fall = 0
                       # not enough data to provide correct calculations
               else:
                   last_prices = last_prices[1:] + [coin_price]
    
           #print(f'{coin_name}USDT')
           my_coins[coin_name]['last_prices'] = last_prices # перезапись всего массива цен с добавленной текущей ценой 
           price=client.klines(f'{coin_name}USDT', "5m", limit=4) # как вариант здесь использовать 2-3 5М бара???? 
           high=[float(price[x][2]) for x in range(len(price))]
           low=[float(price[x][3]) for x in range(len(price))]
           min_high=high[low.index(min(low[:-1]))]
           my_coins[coin_name]['cur_buy_price'] =min_high # Min_High за последние 5 закрытых минуток 
           my_coins[coin_name]['cur_stop_price'] =round(min(low[:-1])*(1-0.04/100),5) # Min_Low за последние 5 закрытых минуток 
           my_coins[coin_name]['cur_take_profit'] =round(min_high+(min_high/100)*coin['net_step_level%'],5) # Расчет цены первого уровня профита по заданному значению % цены
            params_buy = {
           'symbol': f'{coin_name}USDT',
           'side': 'BUY',
           'type': 'MARKET',
           #'timeInForce': 'GTC',
           'quantity': my_coins[coin_name]['amount']
           #'price': 28982.5
            }
           params_oco = {
           "symbol": f'{coin_name}USDT',
           "side": "SELL",
           "quantity": my_coins[coin_name]['amount'],
           "price": round(my_coins[coin_name]['cur_take_profit'],2),
           "stopPrice": round(my_coins[coin_name]['cur_stop_price'],2),
           "stopLimitPrice": round(my_coins[coin_name]['cur_stop_price']*(1-round(0.025/100,1)),2),
           "stopLimitTimeInForce": "GTC"
            }
    
           message = ''
# (логика, которая формирует сообщение о том, что пора покупать/продавать/ничего не делать)
           temp=check_asset(coin_name,my_coins[coin_name]['init_depo'],client.account(recvWindow=6000)['balances']) # возврат dict полей 'free' и 'locked' актива
           if temp['locked']>0 : # блок установки трейлинг стопа
               new_stop=round(high[-1]-(coin_price/100)*coin['tral%'],2)
               if round(last_stop_loss(client.get_open_orders(f'{coin_name}USDT')),2)<new_stop>coin['last_enter_price']+(coin_price/100)*coin['commis%']: # вводим учет коммисии
                   if type(client.cancel_open_orders(f'{coin_name}USDT'))==list: # отмена старых ордеров
                       message += f'{coin_name} ->Cancel of the old OCO order is SUCCESSFUL!\n'
                   else: message +=f'{coin_name} ->ERROR -->Cancel old OCO order:(\n' 
                   params_nextoco = {
                   "symbol": f'{coin_name}USDT',
                   "side": "SELL",
                   "quantity": temp['locked'],
                   "price": round(my_coins[coin_name]['cur_take_profit'],2), #???
                   "stopPrice": round(new_stop*(1+round(0.025/100,1)),2),
                   "stopLimitPrice": round(new_stop,2),
                   "stopLimitTimeInForce": "GTC"
                    }
                   if type(client.new_oco_order(**params_nextoco))==dict: # открываем ОСО ордер с новыми уровнями Stop_Loss и Take_Profit
                        message += f'{coin_name} ->NEW_Trailing STOP_LOSS set to: {round(new_stop,5)} level! \n last_enter_price: {round(coin["last_enter_price"],5)}'
                   else: message +=f'{coin_name} ->ERROR -->NEW_Trailing STOP now:(' 
           time.sleep(1)
           temp=check_asset(coin_name,my_coins[coin_name]['init_depo'],client.account(recvWindow=6000)['balances']) # возврат dict полей 'free' и 'locked' актива (определяется по полю есть ли обьем актива без OCO_order)
           if temp['free']>0 :#coin_price >= coin['desired_sell_price'] and coin['amount'] > 0:
               params_newoco = {
               "symbol": f'{coin_name}USDT',
               "side": "SELL",
               "quantity": temp['free'],
               "price": round(my_coins[coin_name]['cur_take_profit'],2),
               "stopPrice": round(my_coins[coin_name]['cur_stop_price'],2),
               "stopLimitPrice": round(my_coins[coin_name]['cur_stop_price']*(1-round(0.025/100,1)),2),
               "stopLimitTimeInForce": "GTC"
                }
               if type(client.new_oco_order(**params_newoco))==dict: # открываем ОСО ордер на закрытие ордера по Stop_Loss и Take_Profit
                   message += f'{coin_name} ->NEW_OCO_ORDER for STOP_LOSS by: {round(my_coins[coin_name]["cur_stop_price"]*(1-round(0.025/100,1)),5)} is open!\n'
               else: message +=f'{coin_name} ->ERROR -->NEW_OCO_ORDER now:(' 
           if temp['locked']==0 and temp['free']==0 and should_i_buy(price_fall, coin['desired_price_fall%'], coin_price): # проверка условия падения цены на desired_price_fall%
               message += f'{coin_name} --> TIME TO BUY\n'
               message += f'price fall = {round(price_fall / coin_price * 100, 1)}%\n'
               pri=float(client.klines(f'{coin_name}USDT', "1m", limit=1)[0][2]) # вызов текущего значения High цены 
               if pri>my_coins[coin_name]['cur_buy_price']: # условие разворота на дне
                   if сheck_open_trades(coin_name,my_coins[coin_name]['init_depo'],client.get_open_orders(f'{coin_name}USDT'),client.account(recvWindow=6000)['balances']):
                       new_order=client.new_order(**params_buy) # размещение маркет ордера на покупку по установленной цене если позиция еще не открыта
                       if type(new_order)==dict: # проверка на успех:)
                           my_coins[coin_name]['last_enter_price']=float(new_order['fills'][0]['price']) # извлечение цены входа
                           time.sleep(1)
                           message += f'{coin_name}->Trade to BUY by price: ~{round(min_high,5)} is open!'
                           if type(client.new_oco_order(**params_oco))==dict: # открываем ОСО ордер на закрытие ордера по Stop_Loss и Take_Profit
                               message += f'{coin_name} -> OCO_ORDER for STOP_LOSS by: {round(my_coins[coin_name]["cur_stop_price"]*(1-round(0.025/100,1)),5)} is open!\n'
                           else: message +=f'{coin_name} ->ERROR -->OCO_ORDER now:(' 
                       else: message +=f'There was an attempt to open a BUY market order now:(' 
                   else: message += 'There are already open positions:)\n'                   
               else: message += f'cur_buy_price: {my_coins[coin_name]["cur_buy_price"]}\ncurent market High: {pri}\n'                
           else: message += ''#f'{coin_name} --> nothing to do right now...'
    
# (обратите внимание на time.sleep(2) - если обращаться к API биржи слишком часто - она вас "забанит" на какое-то время. Так что лучше не спамить запросами)
           if message!='':
               final_message.append(message)
           time.sleep(1)
    
# (после всех операций - записываем обновленные данные в my_cryptocoins.json)
           with open('TM_Trade_Bot\my_cryptocoins.json', 'w') as my_coins_data:
               my_coins_data.write(json.dumps(my_coins, sort_keys=True, indent=2))
    
# (и на конец, команда, которая отправляет финальное сообщение в чат Телеграма)
           if final_message!=[]:
               context.bot.send_message(chat_id=chat_id, text='\n'.join(final_message))
    
# (бот отдыхает 2 сек :) 
           time.sleep(2)  # дабы не бесепокоить Binance слишком частыми запросами
    

# (часть кода для отработки запуска нужной нам функции при отправке боту соответствующей команды)
def main():
   
   updater = Updater(token=TOKEN, use_context=True)
   dp = updater.dispatcher
   dp.add_handler(CommandHandler("start",start, pass_job_queue=True))
   dp.add_handler(CommandHandler('account', req_statement))
   updater.start_polling()
   updater.idle()


if __name__ == '__main__':
   main()
