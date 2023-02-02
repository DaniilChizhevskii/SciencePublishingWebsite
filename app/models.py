from playhouse.sqlite_ext import JSONField
from app.settings import *
from peewee import *


db = SqliteDatabase(db_path)


class ModelSkeleton(Model):
    class Meta:
        database = db


class Admin(ModelSkeleton):
    email = CharField()
    password = CharField()


class BookOrder(ModelSkeleton):
    format = CharField()
    price = FloatField()
    status = CharField()
    created = DateTimeField()
    publication_date = DateField()
    customer_details = JSONField(default=[])
    payment_details = JSONField(default=[])


class Option(ModelSkeleton):
    name = CharField()
    description = CharField()
    structure = CharField()
    value = TextField()


class OptionsManager:
    def __getitem__(self, key):
        option = Option.get(Option.name == key)
        if option.structure == 'int':
            return int(option.value)
        elif option.structure == 'float':
            return float(option.value)
        else:
            return option.value


options = OptionsManager()
