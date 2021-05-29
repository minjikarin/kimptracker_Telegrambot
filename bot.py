
from telegram import Update, Bot, ParseMode
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, MessageHandler, Filters, Defaults
import requests
import re
import os
PORT = int(os.environ.get('PORT', 5000))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
TOKEN = '1780024796:AAGL9_wDpxFfGMOZJEB1Q5ZwOy1TFBrOXc0'

def start(update, context):
    start_message = '🇬🇧 Hola, welcome to the bot! \n this bot is providing <b>kimchi premium rate</b> between Upbit(in Korea) and Bitkub(in Thailand).\n /kimpnow -> to check realtime rate \n /alert -->to create an alert (e.g.:/alert 6.5) \n\n'
    start_message += '🇰🇷 안녕하세요, 봇에 온걸 환영합니다! \n 이 봇은 업비트(한국)과 비트컵(태국)사이의 김치프리미엄 퍼센트를 제공합니다. \n /kimpnow --> 현재 김프를 확인하세요 \n /alert --> 알림 받으실 김프 퍼센트를 설정하세요 (예시:/alert 6.5)'
    update.message.reply_text(start_message)

def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    
def exchange_upbit():
    contents_upbit = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-ETH").json()
    price_upbit = contents_upbit[0]['trade_price']
    return price_upbit

def exchange_bitkub():
    contents_bitkub = requests.get("https://api.bitkub.com/api/market/ticker?sym=THB_ETH").json()
    price_bitkub = contents_bitkub['THB_ETH']["last"]
    return price_bitkub

def get_kimp():
    price_upbit = exchange_upbit()
    price_bitkub = exchange_bitkub()
    contents_forex = requests.get("https://quotation-api-cdn.dunamu.com/v1/forex/recent?codes=FRX.KRWTHB").json()
    forex = contents_forex[0]['basePrice']
    kimp_rate = round(((price_upbit/forex-price_bitkub)/price_bitkub)*100,4)
    return kimp_rate

def get_forex_kimp(country_code,value):
    price_upbit = exchange_upbit()
    if country_code == "TH":
        price_bitkub = exchange_bitkub()
        contents_forex = requests.get("https://quotation-api-cdn.dunamu.com/v1/forex/recent?codes=FRX.KRWTHB").json()
        forex = contents_forex[0]['basePrice']
        if value == "forex":
            return forex
        else :
            kimp_rate = round(((price_upbit/forex-price_bitkub)/price_bitkub)*100,4)
            return kimp_rate

def kimpnow(update, context):
    forex = get_forex_kimp("TH","forex")
    kimp = get_forex_kimp("TH","kimp")
    price_upbit = exchange_upbit()
    price_bitkub = exchange_bitkub()
    equal_bitkub = price_bitkub*forex
    f_price_upbit = "{:,.0f}".format(price_upbit)
    f_price_bitkub = "{:,.0f}".format(price_bitkub)
    f_equal_bitkub ="{:,.0f}".format(equal_bitkub)
    kimp_message = f"🇬🇧 Currently kimchi premium rate for ETH is <b>{kimp}%</b>.\n"
    kimp_message += f"Exchange rate : {forex} KRW/THB \n"
    kimp_message += f"Upbit  : {f_price_upbit} KRW \nBitkub : {f_equal_bitkub} KRW ({f_price_bitkub} THB)\n\n"
    kimp_message += f"🇰🇷 현재 이더리움 김프는 <b>{kimp}%</b> 입니다.\n"
    kimp_message += f"환율 : {forex} 원/밧 \n"
    kimp_message += f"업비트 : {f_price_upbit} 원 \n비트컵 : {f_equal_bitkub} 원 ({f_price_bitkub} 밧)\n"
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=kimp_message)
    
def alert(update, context):
    chat_id = update.message.chat_id
    if len(context.args) >= 1:
        rate = context.args[0]
        
        context.job_queue.run_repeating(AlertCallback, interval=60, first=15, context=[rate, chat_id])
        
        response = f"⏳ I will let you know when the kimchi premium of ETH is more than <b>{rate}%</b>. \n"
        response += f"⏳ 이더리움 김프가 <b>{rate}%</b>를 넘을 때 알려드릴게요."
    
    else:
        response = "⚠️ Please provide a rate value after /alert (e.g.:/alert 6.5)\n"
        response += "⚠️ 원하시는 김프 퍼센트를 /alert 과 함께 적어주세요.(예시:/alert 6.5)"
    context.bot.send_message(chat_id=chat_id, text=response)
    
def AlertCallback(context):
    rate = context.job.context[0]
    chat_id = context.job.context[1]
    
    send = False
    spot_rate = get_kimp()
    
    if float(rate) <= float(spot_rate):
            send = True
            
    if send:
        response = f"👋 the kimchi premium of ETH is now <b>{spot_rate}%!</b> \n"
        response += f"👋 지금 이더리움 김프가 <b>{spot_rate}%</b>입니다! \n"

        context.job.schedule_removal()

        context.bot.send_message(chat_id=chat_id, text=response)
        

def main():
    updater = Updater(TOKEN,use_context=True,defaults=Defaults(parse_mode=ParseMode.HTML))
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("kimpnow",kimpnow))
    dp.add_handler(CommandHandler("alert", alert, pass_args=True))
    dp.add_error_handler(error)
    updater.start_webhook(listen="0.0.0.0",
                          port=int(PORT),
                          url_path=TOKEN)
    updater.bot.setWebhook('https://yourherokuappname.herokuapp.com/' + TOKEN)
    updater.idle()

if __name__ == '__main__':
    main()
