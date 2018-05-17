from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from app import app

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.BigInteger, primary_key=True)
    last_tweet_id = db.Column(db.BigInteger, nullable=True)
    oauth_token = db.Column(db.String(255))
    oauth_token_secret = db.Column(db.String(255))
    search_limit = db.Column(db.Integer, nullable=True)
    search_limit_reset = db.Column(db.DateTime, nullable=True)


class Stats(db.Model):
    __tablename__ = 'stats'
    id = db.Column(db.Integer, primary_key=True)
    last_update = db.Column(db.DateTime, default=datetime.now)

    @classmethod
    def get_singleton(cls):
        instance = db.session.query(cls).first()

        if instance is None:
            instance = cls()
            db.session.add(instance)
            db.session.commit()

        return instance
