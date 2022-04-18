import time
import json
from telegram.ext import Updater, CommandHandler
from calculations import get_price, count_profit, count_price_fall, should_i_buy

# You Telegram Token:
TOKEN = '1111111111:sdfklsdjgkljfdglkDSFDGFDGFDkdjskfljdkf'

# Main bot func:
def make_money(update, context):
# (получаете id чата, где бот будет общаться с вами)
   chat_id = update.effective_chat.id

# (бесконечный цикл)
   while True:
# (открываете файл my_cryptocoins.json и читаете из него данные)
       with open('my_cryptocoins.json', 'r') as my_coins_data:
           my_coins = json.loads(my_coins_data.read())

# (эта переменная будет содержать в себе тот сообщение, которое бот вам отправит в Телеграме)
       final_message = []

# (цикл, проходящий по всем токенам, перечисленным в my_cryptocoins.json)
       for coin_name in my_coins.keys():
           coin = my_coins[coin_name]
           coin_price = get_price(coin_name)

           possible_profit = count_profit(coin, coin_price)
           price_fall = count_price_fall(coin, coin_price)
           last_prices = coin['last_prices']

# (часть кода, отвечающая за работу с ценами, обновляемыми каждую минуту)
           if len(last_prices) <= 60:
               last_prices.append(coin_price)
               if len(last_prices) <= 59:
                   price_fall = 0
                   # not enough data to provide correct calculations
           else:
               last_prices = last_prices[1:] + [coin_price]

           my_coins[coin_name]['last_prices'] = last_prices
           message = ''
# (логика, которая формирует сообщение о том, что пора покупать/продавать/ничего не делать)
           if coin_price >= coin['desired_sell_price'] and coin['amount'] > 0:
               message += f'{coin_name} --> TIME TO SELL\n'
               message += f'possible profit = {possible_profit}$'
           else:
               if should_i_buy(price_fall, coin['desired_price_fall'], coin_price):
                   message += f'{coin_name} --> TIME TO BUY\n'
                   message += f'price fall = {round(price_fall / coin_price * 100, 1)}%'
               else:
                   message += f'{coin_name} --> nothing to do right now...'

# (обратите внимание на time.sleep(2) - если обращаться к API биржи слишком часто - она вас "забанит" на какое-то время. Так что лучше не спамить запросами)
           final_message.append(message)
           time.sleep(2)

# (после всех операций - записываем обновленные данные в my_cryptocoins.json)
       with open('my_cryptocoins.json', 'w') as my_coins_data:
           my_coins_data.write(json.dumps(my_coins, sort_keys=True, indent=2))

# (и наконец, команда, которая отправляет финальное сообщение в чат Телеграма)
       context.bot.send_message(chat_id=chat_id, text='\n'.join(final_message))

# (бот засыпает на 1 минуту до следующей итерации бесконечного цикла)
       time.sleep(60)  # run every minute

# (здесь от вас уже практически ничего не зависит, эта часть кода нужна, чтобы корректно запускать нужную нам функцию при отправке боту соответствующей команды)
def main():
   updater = Updater(token=TOKEN, use_context=True)
   dp = updater.dispatcher
   dp.add_handler(CommandHandler('make_money', make_money))
   updater.start_polling()
   updater.idle()


if __name__ == '__main__':
   main()
