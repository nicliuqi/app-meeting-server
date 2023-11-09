# -*- coding: utf-8 -*-
# @Time    : 2023/10/13 9:54
# @Author  : Tom_zc
# @FileName: clean_logoff_user.py
# @Software: PyCharm
import logging
from django.core.management.base import BaseCommand
from openeuler.models import User, GroupUser, Meeting, Collect, Activity, ActivityCollect
from django.db import transaction
from app_meeting_server.utils.common import get_cur_date

logger = logging.getLogger('log')


class Command(BaseCommand):
    def handle(self, *args, **options):
        cur = get_cur_date()
        logout_users = User.objects.filter(is_delete=1)
        for user in logout_users:
            if cur >= user.logoff_time:
                user_id = user.id
                logger.info("The user(userid:{}) arrival retention time, start to delete".format(str(user_id)))
                with transaction.atomic():
                    ret = GroupUser.objects.filter(user_id=user_id).delete()
                    logger.info("delete groupuser and result is:{}".format(str(ret)))
                    ret = Meeting.objects.filter(user_id=user_id).delete()
                    logger.info("delete meeting and result is:{}".format(str(ret)))
                    ret = Collect.objects.filter(user_id=user_id).delete()
                    logger.info("delete meeting collect and result is:{}".format(str(ret)))
                    ret = Activity.objects.filter(user_id=user_id).delete()
                    logger.info("delete activity and result is:{}".format(str(ret)))
                    ret = ActivityCollect.objects.filter(user_id=user_id).delete()
                    logger.info("delete activity collect and result is:{}".format(str(ret)))
                    ret = User.objects.filter(id=user_id).delete()
                    logger.info("delete user and result is:{}".format(str(ret)))
