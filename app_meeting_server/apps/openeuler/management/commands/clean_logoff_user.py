# -*- coding: utf-8 -*-
# @Time    : 2023/10/13 9:54
# @Author  : Tom_zc
# @FileName: clean_logoff_user.py
# @Software: PyCharm
import logging
import datetime

from django.core.management.base import BaseCommand

from app_meeting_server.utils.permissions import MeetigsAdminPermission, ActivityAdminPermission
from openeuler.models import User, GroupUser, Meeting, Collect, Activity, ActivityCollect, Video, Record
from django.db import transaction
from app_meeting_server.utils.common import get_cur_date

logger = logging.getLogger('log')


class Command(BaseCommand):
    def delete_user_data(self, user_id):
        with transaction.atomic():
            # 1.delete group user
            ret = GroupUser.objects.filter(user_id=user_id).delete()
            logger.info("delete groupuser and result is:{}".format(str(ret)))
            # 2.delete meetings
            ret = Collect.objects.filter(user_id=user_id).delete()
            logger.info("delete meeting collect and result is:{}".format(str(ret)))
            meetings_ids = Meeting.objects.filter(user_id=user_id).values_list("mid", flat=True)
            ret = Video.objects.filter(mid__in=meetings_ids).delete()
            logger.info("delete video and result is:{}".format(str(ret)))
            ret = Record.objects.filter(mid__in=meetings_ids).delete()
            logger.info("delete record and result is:{}".format(str(ret)))
            ret = Meeting.objects.filter(user_id=user_id).delete()
            logger.info("delete meeting and result is:{}".format(str(ret)))
            # 3.delete activity
            ret = ActivityCollect.objects.filter(user_id=user_id).delete()
            logger.info("delete activity collect and result is:{}".format(str(ret)))
            ret = Activity.objects.filter(user_id=user_id).delete()
            logger.info("delete activity and result is:{}".format(str(ret)))
            # 4.delete user
            ret = User.objects.filter(id=user_id).delete()
            logger.info("delete user and result is:{}".format(str(ret)))

    def get_expired_date(self):
        cur = get_cur_date()
        before_date = cur - datetime.timedelta(days=2 * 365)
        before_date_str = datetime.datetime.strftime(before_date, '%Y-%m-%d %H:%M:%S')
        return before_date_str

    def clear_logoff_user(self):
        cur = get_cur_date()
        logout_users = User.objects.filter(is_delete=1)
        for user in logout_users:
            if cur >= user.logoff_time:
                user_id = user.id
                logger.info("The user(userid:{}) arrival retention time, start to delete".format(str(user_id)))
                self.delete_user_data(user_id)

    def clear_expired_user_data(self):
        before_date_str = self.get_expired_date()
        expired_users = User.objects.filter(last_login__lt=before_date_str)
        for user in expired_users:
            if user.level == MeetigsAdminPermission.level or user.activity_level == ActivityAdminPermission.activity_level:
                continue
            user_id = user.id
            logger.info("The user(userid:{}) last login over expired date, start to delete".format(str(user_id)))
            self.delete_user_data(user_id)

    def clear_expired_meetings_data(self):
        before_date_str = self.get_expired_date()
        expired_meetings = Meeting.objects.filter(create_time__lt=before_date_str)
        for meetings in expired_meetings:
            meetings_id = meetings.id
            mid = meetings.mid
            logger.info("The meetings(meetings_id:{}) create time over expired date, start to delete".format(str(meetings_id)))
            ret = Collect.objects.filter(meeting_id=meetings_id).delete()
            logger.info("delete meeting collect and result is:{}".format(str(ret)))
            ret = Video.objects.filter(mid=mid).delete()
            logger.info("delete video and result is:{}".format(str(ret)))
            ret = Record.objects.filter(mid=mid).delete()
            logger.info("delete record and result is:{}".format(str(ret)))
            ret = Meeting.objects.filter(id=meetings_id).delete()
            logger.info("delete meeting and result is:{}".format(str(ret)))

    def clear_expired_activity_data(self):
        before_date_str = self.get_expired_date()
        expired_activitys = Activity.objects.filter(create_time__lt=before_date_str)
        for activitys in expired_activitys:
            activitys_id = activitys.id
            logger.info(
                "The activitys(activitys_id:{}) create time over expired date, start to delete".format(
                    str(activitys_id)))
            ret = ActivityCollect.objects.filter(activity_id=activitys_id).delete()
            logger.info("delete activitys collect and result is:{}".format(str(ret)))
            ret = Activity.objects.filter(id=activitys_id).delete()
            logger.info("delete activitys and result is:{}".format(str(ret)))

    def handle(self, *args, **options):
        logger.info("1.start to check clear_logoff_user")
        try:
            self.clear_logoff_user()
        except Exception as e:
            logger.error("clear_logoff_user {}".format(e))
        logger.info("2.start to check clear_expired_user_data")
        try:
            self.clear_expired_user_data()
        except Exception as e:
            logger.error("clear_expired_user_data {}".format(e))
        logger.info("3.start to check clear_expired_meetings_data")
        try:
            self.clear_expired_meetings_data()
        except Exception as e:
            logger.error("clear_expired_meetings_data {}".format(e))
        logger.info("4.start to check clear_expired_activity_data")
        try:
            self.clear_expired_activity_data()
        except Exception as e:
            logger.error("clear_expired_activity_data {}".format(e))
