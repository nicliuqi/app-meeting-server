import datetime
import logging
from django.core.management import BaseCommand

from app_meeting_server.utils.common import decrypt_openid
from openeuler.models import Collect, Meeting, User
from app_meeting_server.utils import wx_apis

logger = logging.getLogger('log')


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info('start task')
        send_subscribe_msg()


def send_subscribe_msg():
    logger.info('start to search meetings...')
    # 获取当前日期
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    t1 = datetime.datetime.now().strftime('%H:%M')
    t2 = (datetime.datetime.now() + datetime.timedelta(minutes=10)).strftime('%H:%M')
    # 查询当日在t1到t2时段存在的会议
    meetings = Meeting.objects.filter(is_delete=0, date=date, start__gt=t1, start__lte=t2)
    # 若存在符合条件的会议,遍历meetings对每个会议的创建人与收藏者发送订阅消息
    if not meetings:
        logger.info('no meeting found, skip meeting notify.')
        return
    # 获取access_token
    access_token = wx_apis.get_token()
    for meeting in meetings:
        topic = meeting.topic
        start_time = meeting.start
        meeting_id = meeting.id
        time = date + ' ' + start_time
        mid = meeting.mid
        creater_id = meeting.user_id
        creater_user = User.objects.filter(id=creater_id, is_delete=0).first()
        send_to_list = [creater_user.openid] if creater_user else list()
        collections = Collect.objects.filter(meeting_id=meeting.id)
        collection_users = [collection.user_id for collection in collections]
        user_openid_lists = User.objects.filter(id__in=collection_users, is_delete=0).values_list("openid", flat=True)
        send_to_list.extend(user_openid_lists)
        send_to_list = list(set(send_to_list))
        if not len(send_to_list):
            logger.info('the meeting {} had not been added to Favorites'.format(mid))
        for encrypt_openid in send_to_list:
            openid = decrypt_openid(encrypt_openid)
            # 获取模板
            content = wx_apis.get_start_template(openid, meeting_id, topic, time)
            # 发送订阅消息
            r = wx_apis.send_subscription(content, access_token)
            if r.status_code != 200:
                logger.error('status code: {}'.format(r.status_code))
                logger.error('content: {}'.format(r.json()))
            else:
                nickname = User.objects.get(openid=encrypt_openid).nickname
                if r.json()['errcode'] != 0:
                    logger.warning('Error Code: {}'.format(r.json()['errcode']))
                    logger.warning('Error Msg: {}'.format(r.json()['errmsg']))
                    logger.warning('receiver: {}'.format(nickname))
                else:
                    logger.info('meeting {} subscription message sent to {}.'.format(mid, nickname))