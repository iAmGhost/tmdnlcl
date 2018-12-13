# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect, reverse
from django.contrib import messages
from django.http import Http404
from django.db.models import Max

from tmdnlcl_app.models import AppSetting, TwitterUser, Tweet
from tmdnlcl_app.forms import TweetPostForm, TwitterUserModeForm

from twython import Twython, TwythonError


def get_user(request, raise_if_not_found=False):
    user_id = request.session.get('user_id', None)

    if user_id is None:
        if raise_if_not_found is True:
            raise Http404

        return None
    try:
        return TwitterUser.objects.get(id=user_id)
    except TwitterUser.DoesNotExist:
        if raise_if_not_found is True:
            raise Http404

        return None


def index(request):
    tweets = Tweet.objects.none()

    user = get_user(request)

    if request.method == 'POST':
        mode_form = TwitterUserModeForm(request.POST)

        if mode_form.is_valid():
            user.mode = mode_form.cleaned_data['mode']
            user.save(update_fields=['mode'])
            messages.success(request, "동작 방식이 변경되었습니다.")

    mode_form = TwitterUserModeForm(instance=user)

    if user is not None:
        tweets = user.tweet_set.all().order_by('-submitted_at')

    return render(request, 'tmdnlcl_app/index.html', {
        'tweets': tweets,
        'user': user,
        'mode_form': mode_form,
        'total_users': TwitterUser.objects.count(),
        'last_update': TwitterUser.objects.aggregate(last_update=Max('last_update'))['last_update']
    })


def delete(request, tweet_id):
    user = get_user(request, raise_if_not_found=True)

    try:
        tweet = user.tweet_set.get(id=tweet_id)
        tweet.delete()
        messages.success(request, "삭제하였습니다.")
    except Tweet.DoesNotExist:
        raise Http404

    return redirect(reverse('index'))


def post(request):
    form = TweetPostForm(request.POST, instance=Tweet())

    user = get_user(request, raise_if_not_found=True)

    if form.is_valid():
        try:
            tweet = user.tweet_set.get(id=form.cleaned_data['tweet_id'])
        except Tweet.DoesNotExist:
            raise Http404

        tweet.content = form.cleaned_data['content']
        tweet.post()
        tweet.delete()

        messages.success(request, "트윗을 전송하였습니다.")
    else:
        messages.error(request, form.errors)

    return redirect(reverse('index'))


def login(request):
    setting = AppSetting.get_solo()

    oauth_verifier = request.GET.get('oauth_verifier', None)

    if request.session.get('user_id', None) is not None:
        return redirect(reverse("index"))

    if oauth_verifier is None:
        twitter = Twython(setting.twitter_api_key, setting.twitter_api_secret)

        auth = twitter.get_authentication_tokens(callback_url=request.build_absolute_uri(reverse("login")))

        request.session['oauth_token'] = auth['oauth_token']
        request.session['oauth_token_secret'] = auth['oauth_token_secret']

        return redirect(auth['auth_url'])
    else:
        twitter = Twython(setting.twitter_api_key, setting.twitter_api_secret,
                          request.session['oauth_token'], request.session['oauth_token_secret'])
        token = twitter.get_authorized_tokens(oauth_verifier)

        user, created = TwitterUser.objects.get_or_create(
            id=token['user_id'],
            defaults={'oauth_token': token['oauth_token'], 'oauth_token_secret': token['oauth_token_secret']}
        )

        try:
            request.session['screen_name'] = user.get_user_info()['screen_name']
            request.session['user_id'] = user.id
        except TwythonError:
            if user is not None:
                user.delete()
                messages.warning(request, "뭔가 심상치 않은 일이 생겼습니다. 다시 연동해보세요.")

        return redirect('index')


def logout(request):
    request.session.flush()
    return redirect('index')
