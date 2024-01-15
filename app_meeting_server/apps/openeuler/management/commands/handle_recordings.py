from multiprocessing.dummy import Pool as ThreadPool

from django.core.management.base import BaseCommand
from app_meeting_server.utils.handle_recordings import *


class Command(BaseCommand):
    def handle(self, *args, **options):
        review_upload_results()
        logger.info('-' * 20 + ' BOUNDRY ' + '-' * 20)
        targets = search_target_meeting_ids()
        logger.info('target meeting ids: {}'.format(targets))
        pool = ThreadPool()
        pool.map(handle_recording, targets)
        pool.close()
        pool.join()
        logger.info('All done')