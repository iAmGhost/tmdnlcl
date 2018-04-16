import traceback
import re
import shutil
import os
import time
from tempfile import NamedTemporaryFile

import arrow
import requests

from twython import Twython, TwythonAuthError
from heconvert.converter import e2h

from db import db, User
import settings


pattern = r"(&gt;.+?&lt;)"


def download_file(url, file_obj):
    r = requests.get(url, stream=True)
    shutil.copyfileobj(r.raw, file_obj)


def safe_convert(match_obj):
    text = match_obj.group(0)[4:-4]

    try:
        words = []

        for word in text.split(' '):
            try:
                words.append(e2h(word))
            except KeyError:
                words.append(word)

        return ' '.join(words)
    except KeyError:
        return text


def convert(text):
    return re.sub(pattern, safe_convert, text)


def has_pattern(text):
    return settings.HASH_TAG in text and re.match(pattern, text) is not None


def process_tweet(twitter, tweet):
    text = tweet['text']

    if has_pattern(text):
        media = tweet['extended_entities']['media'][0]

        file_url = media['media_url']

        if media['type'] == 'video':
            for variant in media['video_info']['variants']:
                if variant['content_type'] == 'video/mp4':
                    file_url = variant['url']
                    break

        ext = file_url.split('/')[-1].split('.')[-1]

        if media['type'] == 'photo':
            file_url += ':orig'

        text = text.replace(f"{media['url']}", "").strip()

        with NamedTemporaryFile(suffix=f'.{ext}', delete=False) as f:
            print(f'Downloading {file_url}')
            download_file(file_url, f)
            f.close()

            if media['type'] == 'photo':
                media_id = twitter.upload_media(media=open(f.name, 'rb'))['media_id']
            else:
                media_id = twitter.upload_video(open(f.name, 'rb'), 'video/mp4')['media_id']

            os.unlink(f.name)

        twitter.update_status(status=convert(text), media_ids=[media_id])
        twitter.destroy_status(id=tweet['id'])
        print(f"Processed tweet {tweet['id']}")


def process_user(user):
    print(f"User: {user.id}")

    if user.search_limit == 0 and arrow.get(user.search_limit_reset).replace(tzinfo='Asia/Seoul') > arrow.now():
        print("Rate limit exceeded.")
        return

    twitter = Twython(settings.TWITTER_API_KEY, settings.TWITTER_API_SECRET,
                      user.oauth_token, user.oauth_token_secret)

    try:
        if settings.API_MODE == 'search':
            screen_name = twitter.show_user(user_id=user.id)['screen_name']
            tweets = twitter.search(q=f"from:{screen_name}")['statuses']
        else:
            tweets = twitter.get_user_timeline(user_id=user.id, since_id=user.id)
    except TwythonAuthError:
        db.session.delete(user)
        db.session.commit()
        return

    user.search_limit = int(twitter.get_lastfunction_header('X-Rate-Limit-Remaining', None))
    user.search_limit_reset = arrow.get(twitter.get_lastfunction_header('X-Rate-Limit-Reset', None)) \
        .to('Asia/Seoul') \
        .datetime

    db.session.commit()

    for tweet in tweets:
        try:
            process_tweet(twitter, tweet)
        except Exception:
            traceback.print_exc()

    if len(tweets) > 0:
        user.last_tweet_id = max(tweets, key=lambda t: t['id'])['id']
        db.session.commit()


def run():
    for user in db.session.query(User):
        try:
            process_user(user)
        except Exception:
            traceback.print_exc()


if __name__ == '__main__':
    while True:
        run()
        time.sleep(settings.BATCH_INTERVAL)
