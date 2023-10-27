import datetime
import icalendar
import logging
import pytz
import smtplib
from django.conf import settings
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from openeuler.models import Meeting

logger = logging.getLogger('log')


def sendmail(mid):
    mid = str(mid)
    meeting = Meeting.objects.get(mid=mid)
    date = meeting.date
    start = meeting.start
    end = meeting.end
    toaddrs = meeting.emaillist
    topic = '[Cancel] ' + meeting.topic
    sig_name = meeting.group_name
    platform = meeting.mplatform
    platform = platform.replace('zoom', 'Zoom').replace('welink', 'WeLink')
    start_time = ' '.join([date, start])
    toaddrs = toaddrs.replace(' ', '').replace('，', ',').replace(';', ',').replace('；', ',')
    toaddrs_list = toaddrs.split(',')
    toaddrs_string = ','.join(toaddrs_list)
    toaddrs_list = sorted(list(set(toaddrs_list)))
    if not toaddrs_list:
        logger.info('Event of cancelling meeting {} has no email to send.'.format(mid))
        return

    # 构造邮件
    msg = MIMEMultipart()

    # 添加邮件主体
    body_of_email = None
    with open('app_meeting_server/templates/template_cancel_meeting.txt', 'r', encoding='utf-8') as fp:
        body = fp.read()
        body_of_email = body.replace('{{platform}}', platform). \
            replace('{{start_time}}', start_time). \
            replace('{{sig_name}}', sig_name)
    content = MIMEText(body_of_email, 'plain', 'utf-8')
    msg.attach(content)

    # 取消日历
    dt_start = (datetime.datetime.strptime(date + ' ' + start, '%Y-%m-%d %H:%M') - datetime.timedelta(hours=8)). \
        replace(tzinfo=pytz.utc)
    dt_end = (datetime.datetime.strptime(date + ' ' + end, '%Y-%m-%d %H:%M') - datetime.timedelta(hours=8)). \
        replace(tzinfo=pytz.utc)

    cal = icalendar.Calendar()
    cal.add('prodid', '-//openeuler conference calendar')
    cal.add('version', '2.0')
    cal.add('method', 'CANCEL')

    event = icalendar.Event()
    event.add('attendee', ','.join(sorted(list(set(toaddrs_list)))))
    event.add('summary', topic)
    event.add('dtstart', dt_start)
    event.add('dtend', dt_end)
    event.add('dtstamp', dt_start)
    event.add('uid', platform + mid)
    event.add('sequence', 1)

    cal.add_component(event)

    part = MIMEBase('text', 'calendar', method='CANCEL')
    part.set_payload(cal.to_ical())
    encoders.encode_base64(part)
    part.add_header('Content-class', 'urn:content-classes:calendarmessage')

    msg.attach(part)

    # 完善邮件信息
    msg['Subject'] = topic
    msg['From'] = settings.MESSAGE_FROM
    msg['To'] = toaddrs_string

    # 登录服务器发送邮件
    try:
        sender = settings.SMTP_SERVER_SENDER
        server = smtplib.SMTP(settings.SMTP_SERVER_HOST, settings.SMTP_SERVER_PORT)
        server.ehlo()
        server.starttls()
        server.login(settings.SMTP_SERVER_USER, settings.SMTP_SERVER_PASS)
        server.sendmail(sender, toaddrs_list, msg.as_string())
        server.quit()
        logger.info('send cancel email success: {}'.format(topic))
    except smtplib.SMTPException as e:
        logger.error(e)
