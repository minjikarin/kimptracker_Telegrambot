import logging
from telegram import Update, Bot, ParseMode
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, MessageHandler, Filters, Defaults, Job, JobQueue
import requests
import pyupbit
import re
import os
PORT = int(os.environ.get('PORT', 5000))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

TOKEN = 'YOUR_TELEGRAM_TOKEN'
TOKEN_TEST = 'YOUR_TELEGRAM_TEST_TOKEN'
WEBHOOK_URL = 'YOUR_HEROKU_WEBHOOK_URL'

def start(update, context):
    start_message = '🇬🇧 Hola, welcome to the bot! \n this bot provides <b>kimchi premium rate</b> between Upbit(in Korea) and Bitkub(in Thailand).\n /kimpnow - check realtime rate \n /alert - create an notification \n /status - check current notification setting \n /cancel - cancel your notifications \n /source - check the info \n\n'
    start_message += '🇰🇷 안녕하세요, 봇에 온걸 환영합니다! \n 이 봇은 업비트(한국)과 비트컵(태국)사이의 김치프리미엄 퍼센트를 제공합니다. \n /kimpnow - 현재 김프 확인 \n /alert - 김프알림 설정 \n /status - 설정된 알람 확인 \n /cancel - 알람 취소하기 \n /source - 소스정보 확인'
    update.message.reply_text(start_message)

def source(update, context):
    chat_id = update.message.chat_id
    context.bot.sendChatAction(chat_id=chat_id, action="typing")
    source_message = 'Here is the list of resources for kimptrackerbot.\nkimptrackerbot은 아래의 소스들을 참고합니다 \n'
    source_message += "- Dunamu open forex API\n"
    source_message += "- <a href='https://docs.upbit.com/docs/upbit-quotation-restful-api/'>Upbit REST API</a> \n"
    source_message += "- <a href='https://github.com/bitkub/bitkub-official-api-docs/'>Bitkub REST API</a>\n\n"
    source_message += 'Support fund server and development with tips to <b>minji.eth</b>, Thanks! \n서버유지와 개발을 위해 <b>minji.eth</b>로 코인 지원 해주시면 감사하겠습니다! \n\n'
    source_message += "Questions/feedback to 질문과 피드백은 Twitter <a href='https://twitter.com/kimptrackerbot'>kimptrackerbot</a>"
    update.message.reply_text(source_message,disable_web_page_preview=True)    
    
def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def exchange_upbit(crypto):
    #contents_upbit = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-"+crypto).json()
    #price_upbit = contents_upbit[0]['trade_price']
    price_upbit = pyupbit.get_current_price("KRW-"+crypto)
    return price_upbit

def exchange_bitkub(crypto):
    contents_bitkub = requests.get("https://api.bitkub.com/api/market/ticker?sym=THB_"+crypto).json()
    price_bitkub = contents_bitkub['THB_'+crypto]["last"]
    return price_bitkub

def exchange_bitstamp(crypto):
    contents_bitstamp = requests.get("https://www.bitstamp.net/api/v2/ticker/"+crypto.lower()+"eur").json()
    price_bitstamp = contents_bitstamp["last"]
    return price_bitstamp

def get_kimp(crypto):
    price_upbit = exchange_upbit(crypto)
    price_bitkub = exchange_bitkub(crypto)
    forex = get_forex("THB")
    kimp_rate = round(((price_upbit/forex-price_bitkub)/price_bitkub)*100,3)
    return kimp_rate

def get_forex(fiat_code):
    contents_forex = requests.get("https://quotation-api-cdn.dunamu.com/v1/forex/recent?codes=FRX.KRW"+fiat_code).json()
    forex = contents_forex[0]['basePrice']
    return forex

crypto_list = ["ETH","BTC","XRP","LTC"]

def kimpnow(update, context):
    chat_id = update.message.chat_id
    context.bot.sendChatAction(chat_id=chat_id, action="typing")
    forex = get_forex("THB")
    kimp_message = f"Exchange rate 환율 : <b>{forex} KRW/THB</b>\n\n"
    for crypto in crypto_list:
        kimp = get_kimp(crypto)
        price_upbit = exchange_upbit(crypto)
        price_bitkub = exchange_bitkub(crypto)
        equal_bitkub = price_bitkub*forex
        f_price_upbit = "{:,.0f}".format(price_upbit)
        f_price_bitkub = "{:,.0f}".format(price_bitkub)
        f_equal_bitkub ="{:,.0f}".format(equal_bitkub)
        kimp_message += f"☑️<b>{crypto}</b>\n"
        kimp_message += f"Kimchi premium rate 김프: <b>{kimp}%</b>\n"
        kimp_message += f"Upbit 업비트  : {f_price_upbit} KRW \nBitkub 비트컵 : {f_equal_bitkub} KRW ({f_price_bitkub} THB)\n"
    context.bot.send_message(chat_id=chat_id, text=kimp_message) 

alertdict={}

def alert(update, context):
    chat_id = update.message.chat_id
    context.bot.sendChatAction(chat_id=chat_id, action="typing")
    if len(context.args) >= 3:
        crypto = context.args[0].upper()
        sign = context.args[1]
        rate = context.args[2]
        #if crypto is in crypto_list :
        i=1
        alert_num = i
        alert_id = str(chat_id)+"_"+str(alert_num)
        while i < 4 :
            alert_num = i
            alert_id = str(chat_id)+"_"+str(alert_num)
            if alertdict.get(alert_id) is None:
                alertdict.update({alert_id : [crypto, sign, rate]})
                context.job_queue.run_repeating(AlertCallback, interval=60, first=15, context=[crypto, sign ,rate, chat_id, alert_id])
                print(alertdict)
                response = f"⏳ I will let you know when kimchi premium of <b>{crypto}</b> reaches <b>{rate}%</b>. \n"
                response += f"⏳ <b>{crypto}</b> 김프가 <b>{rate}%</b>될 때 알려드릴게요."
                break
            else :
                i+=1
                continue 
        else : 
            response = "⚠️you reach the maximum number of notifications that you can setup"
            response += "⚠️최대 설정할 수 있는 알람 횟수를 초과하였습니다"

    else:
        print(alertdict)
        response = "⚠️ Please provide crypto and a rate value after /alert (e.g.:/alert ETH > 6.5)\n Mamximum notifications : 3 \n"
        response += "⚠️ 원하시는 코인과 김프 퍼센트를 /alert 과 함께 적어주세요.(예시:/alert ETH > 6.5) \n 최대 설정할수 있는 알람 : 3개"
    context.bot.send_message(chat_id=chat_id, text=response)

    
def status(update,context):
    chat_id = update.message.chat_id
    context.bot.sendChatAction(chat_id=chat_id, action="typing")
    i=0
    alert_num = i
    alert_id = str(chat_id)+"_"+str(alert_num)
    limits=[1,2,3]
    response = f"Current notification status (Maximum # : 3) : \n"
    response +="cancel with /cancel # (e.g.:/cancel 2) \n"
    for i in limits:
        alert_num = i
        alert_id = str(chat_id)+"_"+str(alert_num)
        if alertdict.get(alert_id) is not None:
            if alertdict[alert_id][1] == ">":
                expla = "More"
            else :
                expla = "Less"
            response +=f"⏳#{alert_id[-1]}. when <b>{alertdict[alert_id][0]}</b> is <b>{expla}</b> than <b>{alertdict[alert_id][2]}</b>\n"
    context.bot.send_message(chat_id=chat_id, text=response)
    
def cancel(update,context):
    chat_id = update.message.chat_id
    context.bot.sendChatAction(chat_id=chat_id, action="typing")
    if context.args[0] in ("1","2","3"):
        cancel_num = context.args[0]
        alert_id = str(chat_id)+"_"+str(cancel_num)
        if alertdict.get(alert_id) is not None: 
            alertdict.pop(alert_id)
            print(alertdict)
            response = f"#{context.args[0]} notification have been canceled"
        else :
            response =f"⚠️you don't have #{context.args[0]} notification"
    else :
        response = "⚠️input correct number"
    context.bot.send_message(chat_id=chat_id, text=response)

def AlertCallback(context):
    crypto = context.job.context[0]
    sign = context.job.context[1]
    rate = context.job.context[2]
    chat_id = context.job.context[3]
    alert_id = context.job.context[4]
    
    send = False
    spot_rate = get_kimp(crypto)
    
    if sign == '>':
        if float(rate) <= float(spot_rate):
            send = True
    else :
        if float(rate) >= float(spot_rate):
            send = True
            
    if send:
        response = f"👋 kimchi premium of {crypto} is now <b>{spot_rate}%!</b> \n"
        response += f"👋 지금 {crypto} 김프가 <b>{spot_rate}%</b>입니다! \n"

        context.job.schedule_removal()
        alertdict.pop(alert_id)
        print(alertdict)
        
        context.bot.send_message(chat_id=chat_id, text=response)
        

def main():
    updater = Updater(TOKEN,use_context=True,defaults=Defaults(parse_mode=ParseMode.HTML))
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("source", source))
    dp.add_handler(CommandHandler("kimpnow",kimpnow))
    dp.add_handler(CommandHandler("alert", alert, pass_args=True))
    dp.add_handler(CommandHandler("cancel", cancel, pass_args=True))
    dp.add_handler(CommandHandler("status", status))
    dp.add_error_handler(error)
    updater.start_webhook(listen="0.0.0.0",
                          port=PORT,
                          url_path=TOKEN,
                          webhook_url=WEBHOOK_URL + TOKEN)
    #only when test in jupyter
    #updater.start_polling()
    updater.idle()
    
if __name__ == '__main__':
    main()
