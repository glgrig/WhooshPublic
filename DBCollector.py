'''
Файл сборщика данных. Без него телеграм бот не может строить карту. Для правильной работы должен быть постоянно запущен.
'''
import math
import threading
import time
from queue import Queue
import DB
import Main
import peewee
from CONFIG import *
from DB import Scooters, ScooterActions


def addaction(i,accesstoken,idtoken,q:Queue):
    '''Функция добавляет действие в базу данных. Действия записывают основные изменения происходящие с самокатом. '''
    action = {}
    now = Main.getScooterInfo(accesstoken, idtoken, Main.apiKey, i.code)
    # if now['battery']['power'] != i.latest_power:
    #     i.latest_power = now['battery']['power']
    #     action['power'] = now['battery']['power'] иногда вызывает оишбки, тк сервер не присылыает заряд батареи, пока вырезал
    if "position" in now['state']:
        if abs(Main.DegreesToMeters(now['state']['position']['point']['lat'] - i.latest_lat)) > 3 or abs(
                Main.DegreesToMeters(now['state']['position']['point']['lng'] - i.latest_lng)) > 3:
            dLat = abs(Main.DegreesToMeters(now['state']['position']['point']['lat'] - i.latest_lat))
            dLng = abs(Main.DegreesToMeters(now['state']['position']['point']['lng'] - i.latest_lng))
            # dist_traveled = math.sqrt(dLat * dLat + dLng * dLng)
            i.latest_lat = now['state']['position']['point']['lat']
            i.latest_lng = now['state']['position']['point']['lng']

            action['lat'] = now['state']['position']['point']['lat']
            action['lng'] = now['state']['position']['point']['lng']

        if now['state']['position']['point']['height'] != i.latest_height:
            action['height'] = now['state']['position']['point']['height']
            i.latest_height = now['state']['position']['point']['height']
    if "wheelSpeed" in now['state']:
        if now['state']['wheelSpeed']['amount'] != i.latest_wheelSpeed:
            action['speed'] = now['state']['wheelSpeed']['amount']
            i.latest_wheelSpeed = now['state']['wheelSpeed']['amount']
    if now['state']['status'] != i.latest_status:
        action['status'] = now['state']['status']
        i.latest_status = now['state']['status']
    if now['state']['isOnline'] != i.latest_is_Online:
        action['online'] = now['state']['isOnline']
        i.latest_is_Online = now['state']['isOnline']
    i.save()
    if action:
        q.put([i,action])
def clear_old():
    '''Очищает старые эвенты, ибо хранить дольше какого-то времени смысла не вижу.'''
    return ScooterActions.delete().where(ScooterActions.timestamp<time.time()-EXPIRATION_DELTA).execute()
'''Инициализация подключение к базе данных'''
DB.db.create_tables([ScooterActions,Scooters])
if __name__ =="__main__":
    accesstoken, idtoken = Main.refresh_token(Main.refresh_info)
    while True:
        q = Queue()
        if Main.tokenIsExpired(token=accesstoken,delta=120):
            accesstoken, idtoken = Main.refresh_token(Main.refresh_info)
        scooters = Main.getScooters(accesstoken,idtoken,Main.apiKey,latitude=55.7539303,longitude=37.6185259,radius=1000000)
        cld = clear_old()
        avaliable =[i['code'] for i in scooters]
        i = 1

        for scooter in scooters:
                scootr = Scooters.get_or_none(Scooters.id==scooter['id'])
                if scootr:
                    if scootr.latest_status!='STAND_BY':
                        scootr.latest_status='STAND_BY'
                        scootr.save()
                else:
                    try:

                        Scooters.create(id=scooter['id'],code=scooter['code'],latest_power=scooter['battery']['power'],
                                    latest_lng=scooter['state']['position']['point']['lng'],latest_lat=scooter['state']['position']['point']['lat'],
                                    latest_height=0,latest_wheelSpeed=0,latest_status="STAND_BY",latest_is_Online=True)

                        i+=1
                    except peewee.IntegrityError:
                        pass
        print(f"Added Scooters:{i} Cleared Events:{cld}")
        used = Scooters.select().where(Scooters.code.not_in(avaliable))
        threads = []

        for i in used:
            th = threading.Thread(target=addaction,args=[i,accesstoken,idtoken,q])
            th.start()
            threads.append(th)
        for i in threads:
            i.join()
        while not q.empty():
                rslt = q.get()
                if q.qsize()==0:
                    pass
                ScooterActions.create(timestamp=time.time(), scooter=rslt[0], action=rslt[1])