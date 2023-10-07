import logging
from openeuler.models import User
from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand
from obs import ObsClient

logger = logging.getLogger('log')
GMT_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'


def check_modify_time(now_time, modify_time):
    interval = now_time - modify_time
    if interval.days > 0:
        return False
    if interval.seconds < int(settings.QUERY_INTERVAL):
        return True
    else:
        return False


class Command(BaseCommand):
    def handle(self, *args, **options):
        # 获取当前时间
        now_time = datetime.now()
        # 连接ObsClient
        obs_client = ObsClient(access_key_id=settings.ACCESS_KEY_ID,
                               secret_access_key=settings.SECRET_ACCESS_KEY,
                               server=settings.ENDPOINT)
        metadata = obs_client.getObjectMetadata(settings.BUCKET_NAME, settings.OBJ_KEY)
        if metadata.status != 200:
            logger.error('Failed to get search the target object.')
            return
        gmt_time = metadata.get('body').get('lastModified')
        modify_time = datetime.strptime(gmt_time, GMT_FORMAT)
        need_update = check_modify_time(now_time, modify_time)
        if not need_update:
            logger.info('There is no need to update agreement, exit.')
            return
        User.objects.all().update(agree_privacy_policy=False)
        logger.info('Notice the target object has been modified, update agreement status of all users.')