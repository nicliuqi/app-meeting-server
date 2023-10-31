import logging
import sys
from django.conf import settings
from django.core.management.base import BaseCommand
from meetings.models import Record
from obs import ObsClient
from meetings.utils.bili_apis import get_all_bvids, get_credential, get_user

logger = logging.getLogger('log')


class Command(BaseCommand):
    def handle(self, *args, **options):
        credential = get_credential()
        user = get_user(settings.BILI_UID, credential)
        bvs = get_all_bvids(user)  # 所有过审视频的bvid集合
        logger.info('B站过审视频数: {}'.format(len(bvs)))
        access_key_id = settings.ACCESS_KEY_ID
        secret_access_key = settings.SECRET_ACCESS_KEY
        endpoint = settings.OBS_ENDPOINT
        bucketName = settings.OBS_BUCKETNAME
        if not access_key_id or not secret_access_key or not endpoint or not bucketName:
            logger.error('losing required arguments for ObsClient')
            sys.exit(1)
        obs_client = ObsClient(access_key_id=access_key_id,
                               secret_access_key=secret_access_key,
                               server='https://%s' % endpoint)
        bili_mids = [int(x.mid) for x in Record.objects.filter(platform='bilibili', url__isnull=True)]
        logger.info('所有还未上传B站的会议的mid: {}'.format(bili_mids))
        all_bili_mids = [int(x.mid) for x in Record.objects.filter(platform='bilibili')]
        for mid in all_bili_mids:
            obs_record = Record.objects.get(mid=mid, platform='obs')
            url = obs_record.url
            object_key = url.split('/', 3)[-1]
            # 获取对象的metadata
            metadata = obs_client.getObjectMetadata(bucketName, object_key)
            metadata_dict = {x: y for x, y in metadata['header']}
            if 'bvid' not in metadata_dict.keys():
                logger.info('meeting {}: 未上传B站，跳过'.format(mid))
            else:
                logger.info('meeting {}: bvid为{}'.format(mid, metadata_dict['bvid']))
                if metadata_dict['bvid'] not in bvs:
                    logger.info('meetings: {}: 上传至B站，还未过审或已被删除'.format(mid))
                else:
                    bili_url = 'https://www.bilibili.com/{}'.format(metadata_dict['bvid'])
                    Record.objects.filter(mid=mid, platform='bilibili').update(url=bili_url)
                    logger.info('meeting {}: B站已过审，刷新播放地址'.format(mid))
