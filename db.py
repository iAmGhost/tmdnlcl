from flask_sqlalchemy import SQLAlchemy
from app import app

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.BigInteger, primary_key=True)
    last_tweet_id = db.Column(db.BigInteger, nullable=True)
    oauth_token = db.Column(db.String(255))
    oauth_token_secret = db.Column(db.String(255))
    search_limit = db.Column(db.Integer, nullable=True)
    search_limit_reset = db.Column(db.DateTime, nullable=True)
