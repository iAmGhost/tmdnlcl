import time
import threading
import queue
import collections
import traceback
import pendulum

from django.core.management.base import BaseCommand

from tmdnlcl_app.models import Tweet, TwitterUser, AppSetting

from twython import TwythonAuthError


Media = collections.namedtuple('Media', 'type,url')


class Worker(threading.Thread):
    def __init__(self, name, q, delay):
        super().__init__()
        self.name = name
        self.queue = q
        self.exit = threading.Event()
        self.delay = delay

    def run(self):
        while not self.exit.is_set():
            try:
                user_id = self.queue.get(True, 1)
                user = TwitterUser.objects.get(id=user_id)
            except queue.Empty:
                continue
            except TwitterUser.DoesNotExist:
                self.queue.task_done()
                continue

            first_tweet_id = None

            try:
                print(f"[{self.name}] {user.id} 탐색중")

                for raw_tweet in user.search_tweets("#NintendoSwitch"):
                    if first_tweet_id is None:
                        first_tweet_id = raw_tweet['id']

                    tweet = Tweet.from_raw_tweet(user, raw_tweet)

                    if tweet is not None:
                        print(f"[{self.name}] {user.id} 트윗 발견")

                    if tweet is not None:
                        if user.mode == TwitterUser.MODE_INSTANT:
                            print(f"[{self.name}] {user.id}-{tweet.id} 처리중")

                            tweet.post()
                            tweet.destroy()
                            tweet.delete()
                        else:
                            print(f"[{self.name}] {user.id}-{tweet.id} 트윗 저장함")
                            tweet.destroy()

                if first_tweet_id is not None:
                    user.last_tweet_id = first_tweet_id
                    user.save(update_fields=['last_tweet_id'])
            except TwythonAuthError:
                print(f"[{self.name}] {user.id} 사용자 삭제됨.")
                user.delete()
            except Exception:
                traceback.print_exc()

            self.queue.task_done()

            time.sleep(self.delay)

        print(f"[{self.name}] 끝")


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('threads', default=1, type=int)

    def handle(self, *args, **options):
        setting = AppSetting.get_solo()

        assert setting.twitter_api_key is not None
        assert setting.twitter_api_secret is not None

        threads = options['threads']

        q = queue.Queue(maxsize=threads)

        workers = [Worker(f"Worker-{i}", q, setting.batch_delay) for i in range(threads)]

        for worker in workers:
            worker.start()

        while True:
            try:
                for user in TwitterUser.objects.all():
                    q.put(user.id)
            except KeyboardInterrupt:
                print("종료중...")
                break

        print("작업 종료 대기중...")
        q.join()

        for worker in workers:
            worker.exit.set()
            worker.join()
