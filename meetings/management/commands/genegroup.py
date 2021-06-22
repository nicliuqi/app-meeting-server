import logging
import os
from meetings.models import Group
from django.core.management.base import BaseCommand


logger = logging.getLogger('log')

class Command(BaseCommand):
    def handle(self, *args, **options):
        os.system('test -d meetings/community && rm -rf meetings/community')
        os.system('cd meetings; git clone https://gitee.com/mindspore/community.git')
        etherpad_pre = 'https://etherpad.mindspore.cn/p/meetings-'
        if not Group.objects.filter(name='MSG'):
            Group.objects.create(name='MSG', group_type=2, etherpad=etherpad_pre + 'MSG')
            logger.info('Create group MSG')
        if not Group.objects.filter(name='Tech'):
            Group.objects.create(name='Tech', group_type=3, etherpad=etherpad_pre + 'Tech')
            logger.info('Create group Tech')
        with open('meetings/community/sigs/README.md', 'r') as f:
            for line in f.readlines():
                if line.startswith('| ['):
                    sig_name = line[3:].split(']')[0]
                    if not Group.objects.filter(name=sig_name):
                        Group.objects.create(name=sig_name, group_type=1, etherpad=etherpad_pre + sig_name)
                        logger.info('Create sig {}'.format(sig_name))
                    else:
                        Group.objects.filter(name=sig_name).update(group_type=1, etherpad=etherpad_pre + sig_name)
                        logger.info('Update sig {}'.format(sig_name))
        with open('meetings/community/working-groups/README.md', 'r') as f:
            for line in f.readlines():
                if line.startswith('| ['):
                    sig_name = line[3:].split(']')[0]
                    if not Group.objects.filter(name=sig_name, group_type=1):
                        Group.objects.create(name=sig_name, group_type=1, etherpad=etherpad_pre + sig_name)
                        logger.info('Create sig {}'.format(sig_name))
                    else:
                        Group.objects.filter(name=sig_name).update(group_type=1, etherpad=etherpad_pre + sig_name)
                        logger.info('Update sig {}'.format(sig_name))
        logger.info('Done')
