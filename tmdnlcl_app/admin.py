from django.contrib import admin
from solo.admin import SingletonModelAdmin

from tmdnlcl_app.models import AppSetting


@admin.register(AppSetting)
class AppSettingAdmin(SingletonModelAdmin):
    pass
