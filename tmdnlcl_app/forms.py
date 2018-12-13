from django import forms

from tmdnlcl_app.models import TwitterUser, Tweet


class TweetPostForm(forms.ModelForm):
    tweet_id = forms.IntegerField(widget=forms.HiddenInput())

    class Meta:
        model = Tweet
        fields = ['content']


class TwitterUserModeForm(forms.ModelForm):
    class Meta:
        model = TwitterUser
        fields = ['mode']
        widgets = {
            'mode': forms.RadioSelect
        }
