import datetime
import os

import icalendar
import logging
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


def sendmail(m):
    mid = str(m.get('mid'))
    date = m.get('date')
    start = m.get('start')
    end = m.get('end')
    toaddrs = m.get('toaddrs')
    topic = '[Cancel] ' + m.get('topic')
    sig_name = m.get('sig_name')
    platform = m.get('platform')
    sequence = m.get('sequence')
    sequence += 1
    start_time = ' '.join([date, start])
    toaddrs = toaddrs.replace(' ', '').replace('，', ',').replace(';', ',').replace('；', ',')
    toaddrs_list = toaddrs.split(',')
    error_addrs = []
    for addr in toaddrs_list:
        if not re.match(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$', addr):
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

    # 添加邮件主体
    body = read_content(settings.TEMPLATE_CANCEL_EMAIL)
    body_of_email = body.replace('{{platform}}', platform). \
            replace('{{start_time}}', start_time). \
            replace('{{sig_name}}', sig_name)
    content = MIMEText(body_of_email, 'plain', 'utf-8')
    msg.attach(content)

    # 取消日历
    dt_start = (datetime.datetime.strptime(date + ' ' + start, '%Y-%m-%d %H:%M') - datetime.timedelta(hours=8)).replace(
        tzinfo=pytz.utc)
    dt_end = (datetime.datetime.strptime(date + ' ' + end, '%Y-%m-%d %H:%M') - datetime.timedelta(hours=8)).replace(
        tzinfo=pytz.utc)

    cal = icalendar.Calendar()
    cal.add('prodid', '-//openeuler conference calendar')
    cal.add('version', '2.0')
    cal.add('method', 'CANCEL')

    event = icalendar.Event()
    event.add('attendee', toaddrs_string)
    event.add('summary', topic)
    event.add('dtstart', dt_start)
    event.add('dtend', dt_end)
    event.add('dtstamp', dt_start)
    event.add('uid', platform + mid)
    event.add('sequence', sequence)

    cal.add_component(event)

    part = MIMEBase('text', 'calendar', method='CANCEL')
    part.set_payload(cal.to_ical())
    encoders.encode_base64(part)
    part.add_header('Content-class', 'urn:content-classes:calendarmessage')

    msg.attach(part)

    sender = settings.SMTP_SERVER_SENDER
    # 完善邮件信息
    msg['Subject'] = topic
    msg['From'] = 'openGauss conference<%s>' % sender
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