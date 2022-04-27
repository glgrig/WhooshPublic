'''Файл инициализации базы данных, тут ничего интересного не происходит.'''
import peewee
from playhouse.sqlite_ext import JSONField
from playhouse.sqliteq import SqliteQueueDatabase

db = SqliteQueueDatabase('DB.db',pragmas=[('journal_mode', 'wal')])
db.connect()
class BaseModel(peewee.Model):
    class Meta:
        database = db
class Scooters(BaseModel):
    id = peewee.CharField(primary_key=True)
    code = peewee.CharField(unique=True)
    latest_power = peewee.IntegerField()
    latest_lng = peewee.FloatField()
    latest_lat=peewee.FloatField()
    latest_height=peewee.FloatField()
    latest_wheelSpeed=peewee.FloatField()
    latest_status = peewee.CharField()
    latest_is_Online = peewee.BooleanField()
class ScooterActions(BaseModel):
    id=peewee.IntegerField(primary_key=True)
    timestamp = peewee.IntegerField()
    scooter=peewee.ForeignKeyField(Scooters)
    action = JSONField()