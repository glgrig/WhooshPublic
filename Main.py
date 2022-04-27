'''
Главный файл телеграм бота. При первом запуске запросит авторизацию через мобильный номер.
Если давно не запускали бот и он ломается при запуске удалите файл "auth_session.json", должно помочь.

P.S Для нормальной работы бота обязательно постоянно собирать базу через DBCollector.py, запустите сначала его.
'''

import base64
import io
import json
import logging
import time
from datetime import datetime
from telegram import Update, Location, InlineKeyboardMarkup, InlineKeyboardButton
import DB
from Authentication import AuthClass
import gmplot
import requests
from CONFIG import *
from telegram.ext import Updater, Filters, MessageHandler, CommandHandler, CallbackQueryHandler, CallbackContext

from DB import Scooters, ScooterActions, db

def refresh_token(refresh_data):
    '''Обновляет токены авторизации'''
    headers = {
        'Content-Type': 'application/x-amz-json-1.1',
        'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth',
        'User-Agent': 'aws-sdk-android/2.18.0 Linux/4.0.9 Dalvik/2.1.0/0 ru_RU',
        'aws-sdk-retry': '0/0',
        'Accept-Encoding': 'identity',
        'aws-sdk-invocation-id': '36305947-fa36-4088-be6b-3824e9b15d77',
        'Content-Length': '3289',
        'Host': 'cognito-idp.us-east-1.amazonaws.com',
        'Connection': 'Keep-Alive'
    }
    resp = requests.post('https://cognito-idp.us-east-1.amazonaws.com/',headers=headers,data=json.dumps(refresh_info))
    resp_json=resp.json()
    return resp_json['AuthenticationResult']['AccessToken'],resp_json['AuthenticationResult']['IdToken']
try:
    refresh_info = json.loads(open('auth_session.json').read())
except:
    '''Bad code but that is how we do POC'''
    auth = AuthClass()
    while True:
        try:
            auth.SendSmsRequest(input("Enter a VALID phone number to recive an sms code:"))
            break
        except:
            pass
    while True:
        try:
            auth.AuthorizeWithCode(input("Enter the code from the sms:"))
            break
        except:
            print("The code you entered is probably invalid, try again.")
    refresh_info ={"AuthFlow":"REFRESH_TOKEN_AUTH",
                   "AuthParameters":
                        {"SECRET_HASH":""
                        },
                   "ClientId": "7g1h82vpnjve0omfq1ssko18gl"
                   }
    refresh_info['AuthParameters']['REFRESH_TOKEN'] = auth.RefreshToken
    with open('auth_session.json','w') as f:
        f.write(json.dumps(refresh_info))
apiKey = 'yqKeRnxGX77NSeqvX3YyQ5VBio3SJcJ44iOfOnBX'

def metersToDegrees(meters:int):
    '''Перевод метров в градусы широты/долготы'''
    return meters/111139
def DegreesToMeters(degrees:int):
    '''Перевод градусов широты/долготы в метры'''
    return degrees*111139
def tokenIsExpired(token,delta:int=60 ):
    '''Проверяет кончился ли срок действия токена'''
    encodedMetadata = token.split('.')[1]
    decodedMetadata = json.loads(base64.b64decode(encodedMetadata+'===').decode('utf-8'))
    expiration = decodedMetadata['exp']
    if int(expiration)<time.time()+delta:
        return True
    else:
        return False
def getScooters(accesstoken,idtoken,apikey,latitude,longitude,radius,regionId="773ff572-49a8-4619-b291-290f1f3e4271"):#radius is actually not a circle but a square around the point
    '''Получает все самокаты на которых не едут люди в радиусе от заданой точки.
     (ХА на самом деле я настолько ленивый, что тут не круг, а квадрат)'''
    headers = {
        'X-Auth-Token': accesstoken,
        'X-Api-Key': apikey,
        'X-Id-Token': idtoken,
        'X-Client': 'android',
        'User-Agent':'okhttp/3.14.9',
        'X-Api-Version': '1.0',
        'X-Client-Version': '1.6.6',
        'Content-Type': 'application/json'
    }
    deltaDegrees = metersToDegrees(radius)
    data = {"clientSearchDevicesParams":{"regionId":regionId,"visibleArea":{"bottomRight":{"lat":latitude-deltaDegrees,"lng":longitude+deltaDegrees},"upperLeft":{"lat":latitude+deltaDegrees,"lng":longitude-deltaDegrees}}}}
    response = requests.post('https://api.whoosh.bike/v0/client/devices/searches',headers=headers,data=json.dumps(data))
    return response.json()['devices']
def getScooterInfo(accesstoken,idtoken,apikey,ScooterCode):
    '''Получает актуальную информацию о самокате из API Whoosh'''
    headers = {
        'X-Auth-Token': accesstoken,
        'X-Api-Key': apikey,
        'X-Id-Token': idtoken,
        'X-Client': 'android',
        'User-Agent': 'okhttp/3.14.9',
        'X-Api-Version': '1.0',
        'X-Client-Version': '1.5.2',
        'Content-Type': 'application/json'
    }
    response = requests.get(f'https://api.whoosh.bike/v0/devices/state?code={ScooterCode}',headers=headers)
    return response.json()['device']
def send_beep(accesstoken,idtoken,apikey,scooterId,latitude,longitude,):
    '''Отдает команду сигналить определенному самокату.'''
    headers = {
        'X-Auth-Token': accesstoken,
        'X-Api-Key': apikey,
        'X-Id-Token': idtoken,
        'X-Client': 'android',
        'X-Api-Version': '1.0',
        'User-Agent': 'okhttp/3.14.9',
        'X-Client-Version': '1.5.2',
        'Content-Type': 'application/json'
    }
    response = requests.post(f'https://api.whoosh.bike/v0/devices/{scooterId}/ring?lat={latitude}&lng={longitude}',headers=headers)
    return response.json()
def Plot(code,period=86400):
    '''Рисует на карте маршрут перемещения самоката'''
    colors = ['red','black','blue','green']
    scooter = Scooters.select().where(Scooters.code==code).first()
    actions = ScooterActions.select().order_by(ScooterActions.timestamp).where((ScooterActions.scooter==scooter)&(ScooterActions.timestamp>time.time()-period))
    latitude_list_of_lists = [[]]
    longitude_list_of_lists= [[]]
    timestamp_list_of_lists=[[]]
    for action in actions:
        try:

            action_action = action.action
            if 'status' in action_action:
                if action_action['status']=='IN_USE' and len(latitude_list_of_lists[0])>1:
                    latitude_list_of_lists.append([])
                    longitude_list_of_lists.append([])
                    timestamp_list_of_lists.append([])
            lat = action_action['lat']
            lng = action_action['lng']
            timestamp = action.timestamp
            latitude_list_of_lists[-1].append(lat)
            longitude_list_of_lists[-1].append(lng)
            timestamp_list_of_lists[-1].append(timestamp)
        except:
            pass
    gmap= gmplot.GoogleMapPlotter(latitude_list_of_lists[0][0],longitude_list_of_lists[0][0],20)
    cnum=0
    for i in range(len(latitude_list_of_lists)):
        gmap.plot(latitude_list_of_lists[i],longitude_list_of_lists[i],edge_width=5,color=colors[cnum])
        gmap.marker(latitude_list_of_lists[i][0],longitude_list_of_lists[i][0], color='green',label='S',title='Начало маршрута',info_window=datetime.fromtimestamp(timestamp_list_of_lists[i][0]).strftime("%d/%m/%Y, %H:%M:%S"))
        gmap.marker(latitude_list_of_lists[i][-1],longitude_list_of_lists[i][-1],color='red',label='F',title="Конец маршрута",info_window=datetime.fromtimestamp(timestamp_list_of_lists[i][-1]).strftime("%d/%m/%Y, %H:%M:%S"))
        cnum+=1
        if cnum==len(colors):
            cnum=0
    return gmap.get()
def PlotScooters(scooters):
    gmap = gmplot.GoogleMapPlotter(55.7518738, 37.616414, 30)
    for sct in scooters:
        info = f'''
                ID:{sct.id}
                Code:{sct.code}
                Power:{sct.latest_power}
                Speed:{sct.latest_wheelSpeed}
                '''
        gmap.marker(sct.latest_lat, sct.latest_lng, color='red', label=sct.code, info_window=info)
    return gmap.get()
def PlotUsed():
    used = Scooters.select().where(Scooters.latest_status =="IN_TRANSIT")
    return PlotScooters(used)
def PlotStolen():
    '''Возвращает карту с украденными самокатами.'''
    used = Scooters.select().where(Scooters.latest_status == "STOLEN")
    return PlotScooters(used)
def PlotCHARGE_REQUIRED():
    '''Возвращает карту с разряжеными самокатами.'''
    used = Scooters.select().where(Scooters.latest_status == "CHARGE_REQUIRED")
    return PlotScooters(used)
def PLotMostPoints(period=86400):
    '''Рисует на карте маршрут перемещения самоката с самым большим количеством перемещений(*)
    Перемещением считается любой сдвиг самоката.
    '''
    cursor = db.execute_sql('''SELECT scooter_id FROM scooteractions
GROUP BY scooter_id
HAVING COUNT(*) = (
                   SELECT MAX(Cnt) 
                   FROM(
                         SELECT COUNT(*) as Cnt
                         FROM scooteractions
                         GROUP BY scooter_id
                        ) tmp
                    )'''
                   )
    fetched = cursor.fetchone()

    return Plot(Scooters.get_by_id(fetched).code,period=period)
def error_callback(update, context):
    '''Кривая обработка ошибок, когда-нибудь она станет прикрасной...'''
    id = update.effective_chat.id
    context.bot.send_message(chat_id=id, text='An error has occured. Check the validity of your input.')
    raise context.error

def start(update,context):
    id = update.effective_chat.id
    help_text = '''
    Доступные команды:
    🚨🚨🚨🚨🚨🚨🚨🚨
    /beep <code> или /beep <lat> <lng> <R> - команда заставляет бибикать самокат(ы) определенные в запросе
    code - код самоката
    ИЛИ
    lat lng - широта и долгота точки для поиска самокатов для отправки сигнала
    R - радиус поиска
    ИЛИ
    можно просто отправить геопозицию для поиска самокатов
    ℹ️ℹ️ℹ️ℹ️ℹ️ℹ️ℹ️ℹ️
    /info <code> - команда показывает актуальную информацию о самокате с кодом code
    📍📍📍📍📍📍📍📍
    /plot - выводит маршрут самоката с самым большим количеством перемещений за последние несколько дней
    ИЛИ
    /plot <code> <time_period> - выводит маршрут перемещения самоката с кодом code за time_period
    🔋🔋🔋🔋🔋🔋🔋🔋🔋
    /charge - выводит карту самокатов требующих зарядку 
    👨🏿‍🦼👨🏿‍🦼👨🏿‍🦼👨🏿‍🦼👨🏿‍🦼👨🏿‍🦼👨🏿‍🦼👨🏿‍🦼
    /used - выводит карту самокатов не доступных на карте.
    '''
    context.bot.send_message(chat_id=id,text=help_text)
class BotInstance():
    def __init__(self,log_file = 'log.txt'):
        self.accesstoken, self.idtoken = refresh_token(refresh_info)
        self.__log_location = log_file
        self.__log_file = open(self.__log_location,'a')
    def _log(self,update:Update):
        lst  ={}
        lst['time'] = str(update.message.date)
        lst['name'] = update.effective_user.name

        lst['text'] = update.effective_message.text
        if update.effective_message.location:
            lst['location'] = update.effective_message.location.to_dict()
        print(str(lst))

        self.__log_file.write(json.dumps(lst)+'\n')
        self.__log_file.flush()
    def bot_beep(self,update, context):
        '''Заставляет бибикать самокаты вокруг указаной пользователем точки в радиусе R
        Формат запроса: /beep {lat} {long} {R}
        или
        /beep {code}
        code - код скутера
        '''
        self._log(update)
        id = update.effective_chat.id
        msg_text = update.message.text
        args = msg_text.replace(',','.').split(' ')
        if len(args)==4:
            command,lat, long, rad = args
            if int(rad) > 50:
                context.bot.send_message(chat_id=id, text="Нет. Просто нет.")
                return
            if tokenIsExpired(self.accesstoken):
                self.accesstoken, self.idtoken = refresh_token(refresh_info)
            scooters = getScooters(self.accesstoken, self.idtoken, apiKey, float(lat), float(long), int(rad))
            for scooter in scooters:
                context.bot.send_message(chat_id=id,
                                         text=f"Scooter:{scooter['code']}\nBeep:{send_beep(self.accesstoken, self.idtoken, apiKey, scooter['id'], scooter['state']['position']['point']['lat'], scooter['state']['position']['point']['lng'])}")
        elif len(args)==2:
            command,code = args
            if tokenIsExpired(self.accesstoken):
                self.accesstoken, self.idtoken = refresh_token(refresh_info)
            scooter = getScooterInfo(self.accesstoken, self.idtoken, apiKey,msg_text.split(' ')[1])
            context.bot.send_message(chat_id=id,
                                     text=f"Scooter:{scooter['code']}\nBeep:{send_beep(self.accesstoken, self.idtoken, apiKey, scooter['id'], scooter['state']['position']['point']['lat'], scooter['state']['position']['point']['lng'])}")
    def info(self,update,context:CallbackContext):
        '''Отправляет пользователю актуальную информацию о самокате на момент запроса.
         Формат запроса: /info {код_самоката}'''
        id = update.effective_chat.id
        msg_text = update.message.text
        code = msg_text.split(' ')[1]
        if tokenIsExpired(self.accesstoken):

            self.accesstoken, self.idtoken = refresh_token(refresh_info)

        sc_info = getScooterInfo(self.accesstoken, self.idtoken, apiKey,code)
        point = sc_info['state']['position']['point']
        info_short = f'''
        ID:`{sc_info['id']}`
        Code:`{sc_info['code']}`
        Status:`{sc_info['status']}`
        Power:`{sc_info['battery']['power']}`
        '''
        more_button = [InlineKeyboardButton("MoreInfo",callback_data=f'more_info {code}')]
        reply_markup = InlineKeyboardMarkup([more_button])
        context.bot.send_location(id,point['lat'],point['lng'])
        context.bot.send_message(chat_id=id,text=info_short,parse_mode='markdown',reply_markup=reply_markup)

    def send_plot(self,update:Update,context:CallbackContext):
        '''Отправляет карту передвижения самоката пользователю.
        Формат запроса: (1) /plot {код_самоката} {период}
                        Период указывает отрезок времени в течении которого надо искать перемещения самоката.
                        (2) /plot
                        При отсутствии параметров выводит путь самоката с самым большим кол-вом перемещений.
        '''
        id = update.effective_chat.id
        msg_text = update.message.text
        params = msg_text.split(' ')
        if len(params)==3:
            code, period=params[1],params[2]
            context.bot.send_document(id, io.StringIO(Plot(code, int(period))), filename="plot.html")
        elif len(params)==1:
            try:
                context.bot.send_document(id, io.StringIO(PLotMostPoints(9999999)), filename="plot.html")
            except Scooters.DoesNotExist:
                context.bot.send_message(id,text = "No scooters found from your request.\n-------------------------\nПо вашему запросу самокатов не найдено.")

        else:
            context.bot.send_message(chat_id=id,text='Укажите параметры по шаблону.')
    def ping(self,update:Update,context:CallbackContext):
        self._log(update)
        context.bot.send_message(update.effective_chat.id,"Pong")
    def used(self,update:Update,context:CallbackContext):
        '''Присылает карту используемых в данный момент самокатов'''
        self._log(update)
        id = update.effective_chat.id
        msg_text = update.message.text
        try:
            context.bot.send_document(id, io.StringIO(PlotUsed()), filename="Used.html")
        except Scooters.DoesNotExist:
            context.bot.send_message(id,text = "No scooters found from your request.\n-------------------------\nПо вашему запросу самокатов не найдено.")
    def stolen(self,update:Update,context:CallbackContext):
        '''Присылает карту украденых самокатов'''
        self._log(update)
        id = update.effective_chat.id
        msg_text = update.message.text
        try:
            context.bot.send_document(id, io.StringIO(PlotStolen()), filename="Stolen.html")
        except Scooters.DoesNotExist:
            context.bot.send_message(id,text = "No scooters found from your request.\n-------------------------\nПо вашему запросу самокатов не найдено.")
    def charge_required(self,update:Update,context:CallbackContext):
        '''Присылает карту разряженных в данный момент самокатов'''
        self._log(update)
        id = update.effective_chat.id
        msg_text = update.message.text
        try:
            context.bot.send_document(id, io.StringIO(PlotCHARGE_REQUIRED()), filename="ChargeRequired.html")
        except Scooters.DoesNotExist:
            context.bot.send_message(id,text = "No scooters found from your request.\n-------------------------\nПо вашему запросу самокатов не найдено.")
    def geo_handler(self,update:Update,context:CallbackContext):
        '''Отправляет сигналку по геолокации. Пользователь просто скидывет точку геолокации. По дефолту радиус поиска  = 50 метрам.'''
        self._log(update)
        id = update.effective_chat.id
        msg_text = update.message.text
        msg = context.bot.send_message(id,"Погодь, ищу скутеры...")
        long = update.effective_message.location.longitude
        lat = update.effective_message.location.latitude
        rad = 50
        if tokenIsExpired(self.accesstoken):
            self.accesstoken, self.idtoken = refresh_token(refresh_info)
        scooters = getScooters(self.accesstoken, self.idtoken, apiKey, float(lat), float(long), int(rad))
        if len(scooters)==0:
            msg.edit_text('Самокатов не нашел. Попробуй другую точку.')
        msg.edit_text('Сигналю...')
        for scooter in scooters:
            context.bot.send_message(chat_id=id,
                                     text=f"Scooter:{scooter['code']}\nBeep:{send_beep(self.accesstoken, self.idtoken, apiKey, scooter['id'], scooter['state']['position']['point']['lat'], scooter['state']['position']['point']['lng'])}")
        msg.delete()
    def callback_handler(self,update:Update,context:CallbackContext):
        query = update.callback_query
        args = query.data.split(' ')
        if args[0]=='more_info':
            if tokenIsExpired(self.accesstoken):
                self.accesstoken, self.idtoken = refresh_token(refresh_info)

            sc_info = getScooterInfo(self.accesstoken, self.idtoken, apiKey, args[1])
            query.edit_message_text(str(sc_info))
if __name__ =="__main__":
    btinst = BotInstance()
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher


    start_handler = CommandHandler('start', start)
    beepHandler = CommandHandler('beep', btinst.bot_beep)
    infohandler = CommandHandler('info',btinst.info)
    plothandler =CommandHandler('plot',btinst.send_plot)
    pinghandler = CommandHandler('ping',btinst.ping)
    usedhandler = CommandHandler('used',btinst.used)
    stolenhandler = CommandHandler('stolen',btinst.stolen)
    callbackhandler = CallbackQueryHandler(btinst.callback_handler)
    chargerequiredhandler = CommandHandler('charge',btinst.charge_required)
    geo_handler = MessageHandler(Filters.location,btinst.geo_handler)
    dispatcher.add_handler(geo_handler)
    dispatcher.add_handler(infohandler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(beepHandler)
    dispatcher.add_handler(plothandler)
    dispatcher.add_handler(pinghandler)
    dispatcher.add_handler(usedhandler)
    dispatcher.add_handler(stolenhandler)
    dispatcher.add_handler(chargerequiredhandler)
    dispatcher.add_handler(callbackhandler)
    dispatcher.add_error_handler(error_callback)

    updater.start_polling()
