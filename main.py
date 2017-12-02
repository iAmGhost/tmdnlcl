# -*- coding: utf-8 -*-
from flask import Flask, request, session
from twython import Twython, TwythonError
from peewee import IntegrityError

from db import User
import settings

app = Flask(__name__)
app.secret_key = settings.APP_SECRET


@app.route("/")
def index():
    oauth_verifier = request.args.get('oauth_verifier', None)

    if oauth_verifier is None:
        twitter = Twython(settings.TWITTER_API_KEY, settings.TWITTER_API_SECRET)

        auth = twitter.get_authentication_tokens(callback_url=settings.CALLBACK_URL)

        session['oauth_token'] = auth['oauth_token']
        session['oauth_token_secret'] = auth['oauth_token_secret']

        return f"<a href='{auth['auth_url']}'>등록</a>"

    try:
        twitter = Twython(settings.TWITTER_API_KEY, settings.TWITTER_API_KEY,
                          session['oauth_token'], session['oauth_token_secret'])
        token = twitter.get_authorized_tokens(oauth_verifier)
    except TwythonError:
        return "뭐지"

    try:
        User.create(id=int(token['user_id']), oauth_token=token['oauth_token'],
                    oauth_token_secret=token['oauth_token_secret'])
    except IntegrityError:
        pass

    return "등록됐슴"


if __name__ == '__main__':
    app.run()
