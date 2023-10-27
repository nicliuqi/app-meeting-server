import datetime
import icalendar
import logging
import pytz
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.conf import settings
from mindspore.models import Meeting

logger = logging.getLogger('log')


def sendmail(mid, record=None):
    mid = str(mid)
    meeting = Meeting.objects.get(mid=mid)
    topic = meeting.topic
    date = meeting.date
    start = meeting.start
    end = meeting.end
    join_url = meeting.join_url
    sig_name = meeting.group_name
    toaddrs = meeting.emaillist
    etherpad = meeting.etherpad
    platform = meeting.mplatform
    platform = platform.replace('tencent', 'Tencent').replace('welink', 'WeLink')
    summary = meeting.agenda
    if sig_name == 'Tech':
        sig_name = '专家委员会'
    start_time = ' '.join([date, start])
    toaddrs = toaddrs.replace(' ', '').replace('，', ',').replace(';', ',').replace('；', ',')
    toaddrs_list = toaddrs.split(',')
    toaddrs_string = ','.join(toaddrs_list)

    # 构造邮件
    msg = MIMEMultipart()

    # 添加邮件主体
    body_of_email = None
    portal_zh = settings.PORTAL_ZH
    portal_en = settings.PORTAL_EN
    if not summary and not record:
        with open('app_meeting_server/templates/template_without_summary_without_recordings.txt', 'r',
                  encoding='utf-8') as fp:
            body = fp.read()
            body_of_email = body.replace('{{sig_name}}', '{0}').replace('{{start_time}}', '{1}'). \
                replace('{{join_url}}', '{2}').replace('{{topic}}', '{3}'). \
                replace('{{etherpad}}', '{4}').replace('{{platform}}', '{5}'). \
                replace('{{portal_zh}}', '{6}').replace('{{portal_en}}', '{7}'). \
                format(sig_name, start_time, join_url, topic, etherpad, platform, portal_zh, portal_en)
    elif summary and not record:
        with open('app_meeting_server/templates/template_with_summary_without_recordings.txt', 'r',
                  encoding='utf-8') as fp:
            body = fp.read()
            body_of_email = body.replace('{{sig_name}}', '{0}').replace('{{start_time}}', '{1}'). \
                replace('{{join_url}}', '{2}').replace('{{topic}}', '{3}').replace('{{summary}}', '{4}'). \
                replace('{{etherpad}}', '{5}').replace('{{platform}}', '{6}'). \
                replace('{{portal_zh}}', '{7}').replace('{{portal_en}}', '{8}'). \
                format(sig_name, start_time, join_url, topic, summary, etherpad, platform, portal_zh, portal_en)
    elif not summary and record:
        with open('app_meeting_server/templates/template_without_summary_with_recordings.txt', 'r',
                  encoding='utf-8') as fp:
            body = fp.read()
            body_of_email = body.replace('{{sig_name}}', '{0}').replace('{{start_time}}', '{1}'). \
                replace('{{join_url}}', '{2}').replace('{{topic}}', '{3}'). \
                replace('{{etherpad}}', '{4}').replace('{{platform}}', '{5}'). \
                replace('{{portal_zh}}', '{6}').replace('{{portal_en}}', '{7}'). \
                format(sig_name, start_time, join_url, topic, etherpad, platform, portal_zh, portal_en)
    elif summary and record:
        with open('app_meeting_server/templates/template_with_summary_with_recordings.txt', 'r',
                  encoding='utf-8') as fp:
            body = fp.read()
            body_of_email = body.replace('{{sig_name}}', '{0}').replace('{{start_time}}', '{1}'). \
                replace('{{join_url}}', '{2}').replace('{{topic}}', '{3}').replace('{{summary}}', '{4}'). \
                replace('{{etherpad}}', '{5}').replace('{{platform}}', '{6}'). \
                replace('{{portal_zh}}', '{7}').replace('{{portal_en}}', '{8}'). \
                format(sig_name, start_time, join_url, topic, summary, etherpad, platform, portal_zh, portal_en)
    content = MIMEText(body_of_email, 'plain', 'utf-8')
    msg.attach(content)

    # 添加日历
    dt_start = (datetime.datetime.strptime(date + ' ' + start, '%Y-%m-%d %H:%M') - datetime.timedelta(hours=8)).replace(
        tzinfo=pytz.utc)
    dt_end = (datetime.datetime.strptime(date + ' ' + end, '%Y-%m-%d %H:%M') - datetime.timedelta(hours=8)).replace(
        tzinfo=pytz.utc)

    cal = icalendar.Calendar()
    cal.add('prodid', '-//mindspore conference calendar')
    cal.add('version', '2.0')
    cal.add('method', 'REQUEST')

    event = icalendar.Event()
    event.add('attendee', ','.join(sorted(list(set(toaddrs_list)))))
    event.add('summary', topic)
    event.add('dtstart', dt_start)
    event.add('dtend', dt_end)
    event.add('dtstamp', dt_start)
    event.add('uid', platform + mid)

    alarm = icalendar.Alarm()
    alarm.add('action', 'DISPLAY')
    alarm.add('description', 'Reminder')
    alarm.add('TRIGGER;RELATED=START', '-PT15M')
    event.add_component(alarm)

    cal.add_component(event)

    filename = 'invite.ics'
    part = MIMEBase('text', 'calendar', method='REQUEST', name=filename)
    part.set_payload(cal.to_ical())
    encoders.encode_base64(part)
    part.add_header('Content-Description', filename)
    part.add_header('Content-class', 'urn:content-classes:calendarmessage')
    part.add_header('Filename', filename)
    part.add_header('Path', filename)

    msg.attach(part)

    sender = settings.SMTP_SERVER_SENDER
    # 完善邮件信息
    msg['Subject'] = topic
    msg['From'] = 'MindSpore conference <%s>' % sender
    msg['To'] = toaddrs_string

    # 登录服务器发送邮件
    try:
        server = smtplib.SMTP(settings.SMTP_SERVER_HOST, settings.SMTP_SERVER_PORT)
        server.ehlo()
        server.starttls()
        server.login(settings.SMTP_SERVER_USER, settings.SMTP_SERVER_PASS)
        server.sendmail(sender, toaddrs_list, msg.as_string())
        server.quit()
        logger.info('send create meeting email success: {}'.format(topic))
    except smtplib.SMTPException as e:
        logger.error(e)

