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

from app_meeting_server.utils.file_stream import read_content

logger = logging.getLogger('log')


def sendmail(meeting, record=None):
    mid = meeting.get('mid')
    mid = str(mid)
    topic = meeting.get('topic')
    date = meeting.get('date')
    start = meeting.get('start')
    end = meeting.get('end')
    join_url = meeting.get('join_url')
    sig_name = meeting.get('sig_name')
    toaddrs = meeting.get('emaillist')
    platform = meeting.get('platform')
    platform = platform.replace('zoom', 'Zoom').replace('welink', 'WeLink').replace('tencent', 'Tencent')
    etherpad = meeting.get('etherpad')
    summary = meeting.get('agenda')
    start_time = ' '.join([date, start])
    toaddrs = toaddrs.replace(' ', '').replace('，', ',').replace(';', ',').replace('；', ',')
    toaddrs_list = toaddrs.split(',')
    toaddrs_string = ','.join(toaddrs_list)
    # 发送列表去重，排序
    toaddrs_list = sorted(list(set(toaddrs_list)))
    if not toaddrs_string:
        logger.info('Event of creating meeting {} has no email to send.'.format(mid))
        return

    # 构造邮件
    msg = MIMEMultipart()

    # 添加邮件主体
    body_of_email = None
    portal_zh = settings.PORTAL_ZH
    portal_en = settings.PORTAL_EN
    if not summary and not record:
        body = read_content(settings.TEMPLATE_NOT_SUMMARY_NOT_RECORDING)
        body_of_email = body.replace('{{sig_name}}', '{0}').replace('{{start_time}}', '{1}').\
            replace('{{join_url}}', '{2}').replace('{{topic}}', '{3}').\
            replace('{{platform}}', '{4}').replace('{{etherpad}}', '{5}').\
            replace('{{portal_zh}}', '{6}').replace('{{portal_en}}', '{7}').\
            format(sig_name, start_time, join_url, topic, platform, etherpad, portal_zh, portal_en)
    elif summary and not record:
        body = read_content(settings.TEMPLATE_SUMMARY_NOT_RECORDING)
        body_of_email = body.replace('{{sig_name}}', '{0}').replace('{{start_time}}', '{1}').\
            replace('{{join_url}}', '{2}').replace('{{topic}}', '{3}').\
            replace('{{summary}}', '{4}').replace('{{platform}}', '{5}').\
            replace('{{etherpad}}', '{6}').replace('{{portal_zh}}', '{7}').\
            replace('{{portal_en}}', '{8}').\
            format(sig_name, start_time, join_url, topic, summary, platform, etherpad, portal_zh, portal_en)
    elif not summary and record:
        body = read_content(settings.TEMPLATE_NOT_SUMMARY_RECORDING)
        body_of_email = body.replace('{{sig_name}}', '{0}').replace('{{start_time}}', '{1}').\
            replace('{{join_url}}', '{2}').replace('{{topic}}', '{3}').replace('{{platform}}', '{4}').\
            replace('{{etherpad}}', '{5}').replace('{{portal_zh}}', '{6}').replace('{{portal_en}}', '{7}').\
            format(sig_name, start_time, join_url, topic, platform, etherpad, portal_zh, portal_en)
    elif summary and record:
        body = read_content(settings.TEMPLATE_SUMMARY_RECORDING)
        body_of_email = body.replace('{{sig_name}}', '{0}').replace( '{{start_time}}', '{1}').\
            replace('{{join_url}}', '{2}').replace('{{topic}}', '{3}').\
            replace('{{summary}}', '{4}').replace('{{platform}}', '{5}').\
            replace('{{etherpad}}', '{6}').replace('{{portal_zh}}', '{7}').replace('{{portal_en}}', '{8}').\
            format(sig_name, start_time, join_url, topic, summary, platform, etherpad, portal_zh, portal_en)
    content = MIMEText(body_of_email, 'plain', 'utf-8')
    msg.attach(content)

    # 添加日历
    dt_start = (datetime.datetime.strptime(date + ' ' + start, '%Y-%m-%d %H:%M') - datetime.timedelta(hours=8)).replace(tzinfo=pytz.utc)
    dt_end = (datetime.datetime.strptime(date + ' ' + end, '%Y-%m-%d %H:%M') - datetime.timedelta(hours=8)).replace(tzinfo=pytz.utc)

    cal = icalendar.Calendar()
    cal.add('prodid', '-//openeuler conference calendar')
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
        logger.info('send create meeting email success: {}'.format(topic))
    except smtplib.SMTPException as e:
        logger.error(e)
