from peewee import Model, BigIntegerField, IntegerField, DateTimeField, CharField
from playhouse.db_url import connect

import settings

db = connect(settings.DB_URL)


class User(Model):
    id = BigIntegerField(primary_key=True)
    last_tweet_id = BigIntegerField(null=True)
    oauth_token = CharField(max_length=255)
    oauth_token_secret = CharField(max_length=255)
    search_limit = IntegerField(null=True)
    search_limit_reset = DateTimeField(null=True)

    class Meta:
        database = db
        only_save_dirty = True


db.create_table(User, safe=True)
