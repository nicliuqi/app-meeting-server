import logging
import sys
import yaml
from openeuler.models import Group
from django.core.management.base import BaseCommand
from django.conf import settings
from obs import ObsClient


class Command(BaseCommand):
    logger = logging.getLogger('log')

    def handle(self, *args, **options):
        bucket_name = settings.OBS_BUCKETNAME
        obj_key = settings.SIGS_INFO_OBJECT
        obs_client = ObsClient(access_key_id=settings.ACCESS_KEY_ID,
                               secret_access_key=settings.SECRET_ACCESS_KEY,
                               server='https://%s' % settings.OBS_ENDPOINT)
        res = obs_client.getObject(bucket_name, obj_key)
        if res.status != 200:
            self.logger.error('Fail to get OBS object of sigs info')
            sys.exit(1)
        content = yaml.safe_load(res.body.response.read())
        for sig in content:
            sig_name = sig['group_name']
            maillist = sig['maillist']
            etherpad = settings.ETHERPAD_PREFIX + '{}-meetings'.format(sig_name)
            if not Group.objects.filter(group_name=sig_name):
                Group.objects.create(group_name=sig_name, maillist=maillist, etherpad=etherpad)
                self.logger.info('Create group {}'.format(sig_name))
            else:
                Group.objects.filter(group_name=sig_name).update(maillist=maillist, etherpad=etherpad)
                self.logger.info('Update group {}'.format(sig_name))