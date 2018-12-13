import re
import pendulum
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFit

from heconvert.converter import e2h

from django.db import models
from django.core.files.base import ContentFile

import requests
from solo.models import SingletonModel

from twython import Twython, TwythonRateLimitError

INSTANT_PATTERN = re.compile(r"(&gt;.+?&lt;)")
ARCHIVE_TAG = "//"


def url_to_file(url):
    return ContentFile(requests.get(url).content)


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


class AppSetting(SingletonModel):
    twitter_api_key = models.CharField(max_length=255, blank=True, null=True)
    twitter_api_secret = models.CharField(max_length=255, blank=True, null=True)
    batch_delay = models.IntegerField(default=5)


class TwitterUser(models.Model):
    MODE_INSTANT = 1
    MODE_ARCHIVE = 2

    MODE_CHOICES = (
        (MODE_INSTANT, "즉시 업로드(두벌식 영타 변환)"),
        (MODE_ARCHIVE, "나중에 업로드(텍스트 직접 입력)")
    )

    id = models.BigIntegerField(primary_key=True)
    last_tweet_id = models.BigIntegerField(null=True, blank=True)
    oauth_token = models.CharField(max_length=255)
    oauth_token_secret = models.CharField(max_length=255)
    rate_limit_remaining = models.IntegerField(null=True, blank=True)
    rate_limit_reset = models.DateTimeField(null=True, blank=True)
    mode = models.SmallIntegerField(default=MODE_ARCHIVE, choices=MODE_CHOICES, verbose_name="동작 방식")
    last_update = models.DateTimeField(auto_now=True, db_index=True)

    def get_twitter_api(self):
        setting = AppSetting.get_solo()
        return Twython(setting.twitter_api_key, setting.twitter_api_secret, self.oauth_token, self.oauth_token_secret)

    def get_user_info(self):
        twitter = self.get_twitter_api()
        return twitter.show_user(user_id=self.id)

    def search_tweets(self, keyword):
        if self.rate_limit_remaining == 0 and pendulum.now() < self.rate_limit_reset:
            return []

        twitter = self.get_twitter_api()
        screen_name = self.get_user_info()['screen_name']

        try:
            tweets = twitter.search(q=f"from:{screen_name} {keyword}", result_type='recent')['statuses']
        except TwythonRateLimitError:
            tweets = []

        self.rate_limit_remaining = int(twitter.get_lastfunction_header('X-Rate-Limit-Remaining', None))

        limit_reset = twitter.get_lastfunction_header('X-Rate-Limit-Reset', None)

        if limit_reset is not None:
            self.rate_limit_reset = pendulum.from_timestamp(int(limit_reset))

        self.save(update_fields=['rate_limit_remaining', 'rate_limit_reset', 'last_update'])

        return tweets

    def check_text_pattern(self, text):
        if self.mode == TwitterUser.MODE_INSTANT:
            return re.match(INSTANT_PATTERN, text) is not None
        else:
            return text.startswith(ARCHIVE_TAG)


class Tweet(models.Model):
    id = models.BigIntegerField(primary_key=True)
    user = models.ForeignKey('TwitterUser', on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    content = models.TextField()

    @classmethod
    def from_raw_tweet(cls, user, raw_tweet):
        text = raw_tweet['text']

        if user.check_text_pattern(text):
            tweet, _ = Tweet.objects.get_or_create(id=raw_tweet['id'], defaults={'user': user, 'content': text})
            tweet.attachment_set.all().delete()

            for media in raw_tweet['extended_entities']['media']:
                media_url = media['media_url']

                media_ext = media_url.split('/')[-1].split('.')[-1]

                text = text.replace(f"{media['url']}", "").strip()

                if media['type'] == 'video':
                    video_url = ""

                    for variant in media['video_info']['variants']:
                        if variant['content_type'] == 'video/mp4':
                            video_url = variant['url']
                            break

                    attachment = Attachment(
                        tweet=tweet,
                        type=Attachment.VIDEO,
                        ext=media_ext,
                    )

                    attachment.thumbnail.save(f"{tweet.id}_{pendulum.now().timestamp()}_thumb.{media_ext}",
                                              url_to_file(media_url))
                    attachment.file.save(f"{tweet.id}_{pendulum.now().timestamp()}.mp4",
                                         url_to_file(video_url))

                    attachment.save()

                    break
                elif media['type'] == 'photo':
                    media_url += ':orig'

                    attachment = Attachment(
                        tweet=tweet,
                        type=Attachment.PHOTO,
                        ext=media_ext,
                    )
                    attachment.thumbnail.save(f"{tweet.id}_{pendulum.now().timestamp()}_thumb.{media_ext}",
                                              url_to_file(media_url))
                    attachment.file.save(f"{tweet.id}_{pendulum.now().timestamp()}.{media_ext}", url_to_file(media_url))

                    attachment.save()

            tweet.content = text
            tweet.save(update_fields=['content'])

            return tweet

        return None

    def get_converted_content(self):
        text = self.content.strip()

        if self.user.mode == TwitterUser.MODE_INSTANT:
            text = re.sub(INSTANT_PATTERN, safe_convert, text)
        else:
            if text.startswith(ARCHIVE_TAG):
                text = text[len(ARCHIVE_TAG):]

        return text

    def post(self):
        twitter = self.user.get_twitter_api()

        media_ids = []

        for attachment in self.attachment_set.all():
            if attachment.type == Attachment.VIDEO:
                media_id = twitter.upload_video(open(attachment.file.path, "rb"), 'video/mp4')['media_id']
            else:
                media_id = twitter.upload_media(media=open(attachment.file.path, "rb"))['media_id']

            media_ids.append(media_id)

        twitter.update_status(status=self.get_converted_content(), media_ids=media_ids)

    def destroy(self):
        twitter = self.user.get_twitter_api()
        twitter.destroy_status(id=self.id)


class Attachment(models.Model):
    PHOTO = "photo"
    VIDEO = "video"

    TYPE_CHOICES = (
        (PHOTO, "사진"),
        (VIDEO, "동영상"),
    )

    tweet = models.ForeignKey('Tweet', on_delete=models.CASCADE)
    type = models.CharField(max_length=5, choices=TYPE_CHOICES)
    ext = models.CharField(max_length=5)
    thumbnail = ProcessedImageField(processors=[ResizeToFit(width=280)], format='JPEG', options={'quality': 60})
    file = models.FileField()
