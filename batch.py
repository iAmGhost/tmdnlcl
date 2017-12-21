import re
import shutil
import os
import time
from tempfile import NamedTemporaryFile

import arrow
import requests

from twython import Twython, TwythonAuthError
from heconvert.converter import e2h

from db import User
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
            file_url = media['video_info']['variants'][0]['url']

        ext = file_url.split('/')[-1].split('.')[-1]

        if media['type'] == 'photo':
            file_url += ':orig'

        text = text.replace(f"{media['url']}", "").strip()

        with NamedTemporaryFile(suffix=f'.{ext}', delete=False) as f:
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
        tweets = twitter.get_user_timeline(user_id=user.id, since_id=user.id)
    except TwythonAuthError:
        user.delete()
        return

    user.search_limit = int(twitter.get_lastfunction_header('X-Rate-Limit-Remaining', None))
    user.search_limit_reset = arrow.get(twitter.get_lastfunction_header('X-Rate-Limit-Reset', None)) \
        .to('Asia/Seoul') \
        .datetime

    user.save()

    for tweet in tweets:
        try:
            process_tweet(twitter, tweet)
        except Exception as e:
            print(e)
            continue

    if len(tweets) > 0:
        user.last_tweet_id = max(tweets, key=lambda t: t['id'])['id']
        user.save()


def run():
    for user in User.select():
        try:
            process_user(user)
        except Exception as e:
            print(e)


if __name__ == '__main__':
    while True:
        run()
        time.sleep(5)
