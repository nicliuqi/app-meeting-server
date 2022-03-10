import datetime
import logging
from meetings.models import Activity
from django.core.management import BaseCommand

logger = logging.getLogger('log')


def update_activity_status():
    logger.info('start to update activity status')
    activities = Activity.objects.filter(is_delete=0, status__in=[3, 4, 5])
    today = datetime.date.today().strftime('%Y-%m-%d')
    for activity in activities:
        if activity.start_date == today and activity.status == 3:
            Activity.objects.filter(id=activity.id).update(status=4)
            logger.info(
                '\nid: {0}\nstart_date: {1}\ntitle: {2}\nsponsor: {3}'.format(activity.id,
                                                                              activity.start_date,
                                                                              activity.title,
                                                                              activity.user.gitee_name))
            logger.info('update activity status from publishing to going.')
        if activity.end_date < today and activity.status == 4:
            Activity.objects.filter(id=activity.id).update(status=5)
            logger.info(
                '\nid: {0}\nend_date: {1}\ntitle: {2}\nsponsor: {3}'.format(activity.id,
                                                                            activity.end_date,
                                                                            activity.title,
                                                                            activity.user.gitee_name))
            logger.info('update activity status from going to completed.')
    logger.info('All done. Waiting for next task...')


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            update_activity_status()
        except Exception as e:
            logger.error(e)

