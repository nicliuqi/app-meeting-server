import datetime
import icalendar
import logging
import os
import pytz
import re
import smtplib
import tempfile
import yaml
from django.conf import settings
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app_meeting_server.utils.common import execute_cmd3
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
    toaddrs = meeting.get('toaddrs')
    platform = meeting.get('platform')
    etherpad = meeting.get('etherpad')
    summary = meeting.get('summary')
    sequence = meeting.get('sequence')
    sequence += 1
    start_time = ' '.join([date, start])
    toaddrs = toaddrs.replace(' ', '').replace('，', ',').replace(';', ',').replace('；', ',')
    toaddrs_list = toaddrs.split(',')
    error_addrs = []
    for addr in toaddrs_list:
        if not re.match(r'^[a-zA-Z0-9+_.-]+(\.[a-zA-Z0-9_-]*)*@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$', addr):
            error_addrs.append(addr)
            toaddrs_list.remove(addr)
    toaddrs_string = ','.join(toaddrs_list)
    # 发送列表默认添加该sig所在的邮件列表
    newly_mapping = settings.MAILLIST_MAPPING_URL
    dir_name = tempfile.gettempdir()
    target_file = os.path.join(dir_name, 'maillist_mapping.yaml')
    execute_cmd3('wget {} -O {}'.format(newly_mapping, target_file))
    if not os.path.exists(target_file):
        logger.error('Fail to get maillist mapping')
    else:
        with open(target_file, 'r') as f:
            maillists = yaml.safe_load(f)
        if sig_name in maillists.keys():
            maillist = maillists[sig_name]
            toaddrs_list.append(maillist)
            logger.info('BCC to {}'.format(maillist))

    if sig_name == 'TC':
        for k, v in maillists.items():
            if v not in toaddrs_list:
                toaddrs_list.append(v)
    toaddrs_list = sorted(list(set(toaddrs_list)))
    logger.info('toaddrs_list: {}'.format(toaddrs_list))

    # 构造邮件
    msg = MIMEMultipart()
    portal_zh = settings.PORTAL_ZH
    portal_en = settings.PORTAL_EN

    # 添加邮件主体
    body_of_email = None
    if not summary and not record:
        body = read_content(settings.TEMPLATE_NOT_SUMMARY_NOT_RECORDING)
        body_of_email = body.replace('{{sig_name}}', '{0}').replace('{{start_time}}', '{1}'). \
            replace('{{join_url}}', '{2}').replace('{{topic}}', '{3}'). \
            replace('{{etherpad}}', '{4}').replace('{{platform}}', '{5}'). \
            replace('{{portal_zh}}', '{6}').replace('{{portal_en}}', '{7}').\
            format(sig_name, start_time, join_url, topic, etherpad, platform, portal_zh, portal_en)
    elif summary and not record:
        body = read_content(settings.TEMPLATE_SUMMARY_NOT_RECORDING)
        body_of_email = body.replace('{{sig_name}}', '{0}').replace('{{start_time}}', '{1}'). \
            replace('{{join_url}}', '{2}').replace('{{topic}}', '{3}').replace('{{summary}}', '{4}'). \
            replace('{{etherpad}}', '{5}').replace('{{platform}}', '{6}'). \
            replace('{{portal_zh}}', '{7}').replace('{{portal_en}}', '{8}').\
            format(sig_name, start_time, join_url, topic, summary, etherpad, platform, portal_zh, portal_en)
    elif not summary and record:
        body = read_content(settings.TEMPLATE_NOT_SUMMARY_RECORDING)
        body_of_email = body.replace('{{sig_name}}', '{0}').replace('{{start_time}}', '{1}'). \
            replace('{{join_url}}', '{2}').replace('{{topic}}', '{3}'). \
            replace('{{etherpad}}', '{4}').replace('{{platform}}', '{5}'). \
            replace('{{portal_zh}}', '{6}').replace('{{portal_en}}', '{7}').\
            format(sig_name, start_time, join_url, topic, etherpad, platform, portal_zh, portal_en)
    elif summary and record:
        body = read_content(settings.TEMPLATE_SUMMARY_RECORDING)
        body_of_email = body.replace('{{sig_name}}', '{0}').replace('{{start_time}}', '{1}'). \
            replace('{{join_url}}', '{2}').replace('{{topic}}', '{3}').replace('{{summary}}', '{4}'). \
            replace('{{etherpad}}', '{5}').replace('{{platform}}', '{6}'). \
            replace('{{portal_zh}}', '{7}').replace('{{portal_en}}', '{8').\
            format(sig_name, start_time, join_url, topic, summary, etherpad, platform, portal_zh, portal_en)
    content = MIMEText(body_of_email, 'plain', 'utf-8')
    msg.attach(content)

    # 添加日历
    dt_start = (datetime.datetime.strptime(date + ' ' + start, '%Y-%m-%d %H:%M') - datetime.timedelta(hours=8)).replace(
        tzinfo=pytz.utc)
    dt_end = (datetime.datetime.strptime(date + ' ' + end, '%Y-%m-%d %H:%M') - datetime.timedelta(hours=8)).replace(
        tzinfo=pytz.utc)

    cal = icalendar.Calendar()
    cal.add('prodid', '-//opengauss conference calendar')
    cal.add('version', '2.0')
    cal.add('method', 'REQUEST')

    event = icalendar.Event()
    event.add('attendee', ','.join(sorted(list(set(toaddrs_list)))))
    event.add('summary', topic)
    event.add('dtstart', dt_start)
    event.add('dtend', dt_end)
    event.add('dtstamp', dt_start)
    event.add('uid', platform + mid)
    event.add('sequence', sequence)

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
    msg['From'] = 'openGauss conference <%s>' % sender
    msg['To'] = toaddrs_string

    # 登录服务器发送邮件
    try:
        server = smtplib.SMTP(settings.SMTP_SERVER_HOST, settings.SMTP_SERVER_PORT)
        server.ehlo()
        server.starttls()
        server.login(settings.SMTP_SERVER_USER, settings.SMTP_SERVER_PASS)
        server.sendmail(sender, toaddrs_list, msg.as_string())
        logger.info('email string: {}'.format(toaddrs))
        logger.info('error addrs: {}'.format(error_addrs))
        logger.info('email sent: {}'.format(toaddrs_string))
        server.quit()
    except smtplib.SMTPException as e:
        logger.error(e)
