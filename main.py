# -*- coding: utf-8 -*-
from app import app
from flask import request, session, render_template
from twython import Twython, TwythonError
import settings
from db import db, User


@app.route("/")
def index():
    oauth_verifier = request.args.get('oauth_verifier', None)

    if oauth_verifier is None:
        twitter = Twython(settings.TWITTER_API_KEY, settings.TWITTER_API_SECRET)

        auth = twitter.get_authentication_tokens(callback_url=settings.CALLBACK_URL)

        session['oauth_token'] = auth['oauth_token']
        session['oauth_token_secret'] = auth['oauth_token_secret']

        return render_template("index.html", auth_url=auth['auth_url'])

    try:
        twitter = Twython(settings.TWITTER_API_KEY, settings.TWITTER_API_KEY,
                          session['oauth_token'], session['oauth_token_secret'])
        token = twitter.get_authorized_tokens(oauth_verifier)
    except TwythonError:
        return "뭐지 앱 인증을 해제하고 다시 하던가 해보세요"

    try:
        user = User(id=int(token['user_id']),
                    oauth_token=token['oauth_token'],
                    oauth_token_secret=token['oauth_token_secret'])
        db.session.add(user)
        db.session.commit()
    except db.exc.IntegrityError:
        db.session.rollback()

    return "등록됐습니다 트윗을 올려보세요"


if __name__ == '__main__':
    db.create_all()
    app.run()
