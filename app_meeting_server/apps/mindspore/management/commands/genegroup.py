import logging
import sys
import yaml
from mindspore.models import Group
from django.core.management.base import BaseCommand
from django.conf import settings
from obs import ObsClient

logger = logging.getLogger('log')


class Command(BaseCommand):

    def handle(self, *args, **options):
        logger.error("start to genegroup...")
        bucket_name = settings.OBS_BUCKETNAME
        obj_key = settings.SIGS_INFO_OBJECT
        obs_client = ObsClient(access_key_id=settings.ACCESS_KEY_ID,
                               secret_access_key=settings.SECRET_ACCESS_KEY,
                               server='https://%s' % settings.OBS_ENDPOINT)
        res = obs_client.getObject(bucket_name, obj_key)
        if res.status != 200:
            logger.error('Fail to get OBS object of sigs info')
            sys.exit(1)
        content = yaml.safe_load(res.body.response.read())
        etherpad_pre = '{}/p/meetings-'.format(settings.ETHERPAD_PREFIX)
        for sig in content:
            sig_name = sig['name']
            group_type = sig['group_type']
            etherpad = etherpad_pre + sig_name
            if not Group.objects.filter(name=sig_name, group_type=group_type):
                Group.objects.create(name=sig_name, group_type=group_type, etherpad=etherpad)
                logger.info('Create group %s' % sig_name)
            else:
                Group.objects.filter(name=sig_name, group_type=group_type).update(etherpad=etherpad)
                logger.info('Update group %s' % sig_name)
