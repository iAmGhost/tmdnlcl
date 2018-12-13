from django.contrib import admin
from solo.admin import SingletonModelAdmin

from tmdnlcl_app.models import AppSetting, TwitterUser, Tweet, Attachment


@admin.register(AppSetting)
class AppSettingAdmin(SingletonModelAdmin):
    pass


@admin.register(TwitterUser)
class TwitterUserAdmin(admin.ModelAdmin):
    list_display = ['id', 'rate_limit_remaining', 'rate_limit_reset', 'mode']


class AttachmentInline(admin.StackedInline):
    model = Attachment
    extra = 1


@admin.register(Tweet)
class TweetAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'submitted_at', 'content']
    inlines = [AttachmentInline]
