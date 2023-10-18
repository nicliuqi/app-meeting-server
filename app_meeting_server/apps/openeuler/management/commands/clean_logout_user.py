# -*- coding: utf-8 -*-
# @Time    : 2023/10/13 9:54
# @Author  : Tom_zc
# @FileName: clean_logout_user.py
# @Software: PyCharm
from django.core.management.base import BaseCommand
from openeuler.models import User, GroupUser, Meeting, Collect, Activity, ActivityCollect
from django.db import transaction
from app_meeting_server.utils.common import get_cur_date


class Command(BaseCommand):
    def handle(self, *args, **options):
        cur = get_cur_date()
        logout_users = User.objects.filter(is_delete=1)
        for user in logout_users:
            if cur >= user.logoff_time:
                user_id = user.id
                with transaction.atomic():
                    GroupUser.objects.filter(user_id=user_id).delete()
                    Meeting.objects.filter(user_id=user_id).delete()
                    Collect.objects.filter(user_id=user_id).delete()
                    Activity.objects.filter(user_id=user_id).delete()
                    ActivityCollect.objects.filter(user_id=user_id).delete()
                    User.objects.filter(user_id=user_id).delete()
