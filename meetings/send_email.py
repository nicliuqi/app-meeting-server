import logging
import os
import random
import re
import smtplib
import yaml
from django.conf import settings
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from templates.get_templates import *

logger = logging.getLogger('log')


def sendmail(topic, date, start, join_url, sig_name, toaddrs, summary=None, record=None, enclosure_paths=None):
    start_time = ' '.join([date, start])
    toaddrs = toaddrs.replace(' ', '').replace('，', ',').replace(';', ',').replace('；', ',')
    toaddrs_list = toaddrs.split(',')
    error_addrs = []
    for addr in toaddrs_list:
        if not re.match(r'^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$', addr):
            error_addrs.append(addr)
            toaddrs_list.remove(addr)
    toaddrs_string = ','.join(toaddrs_list)
    # 发送列表默认添加community和dev的邮件列表
    toaddrs_list.extend(['community@openeuler.org', 'dev@openeuler.org'])
    # 发送列表去重，排序
    toaddrs_list = sorted(list(set(toaddrs_list)))

    texthtml = None
    textplain = None
    imagedir = 'templates/images'

    msg = MIMEMultipart('mixed')
    alternative = MIMEMultipart('alternative')

    if not summary and not record:
        html = get_html_without_summary_without_recordings()
        text = get_txt_without_summary_without_recordings()
        texthtml = html.replace('{{sig_name}}', sig_name).replace('{{start_time}}', start_time).replace('{{topic}}',
                                                                                                        topic).replace(
            '{{join_url}}', join_url)
        textplain = text.replace('{{sig_name}}', sig_name).replace('{{start_time}}', start_time).replace('{{topic}}',
                                                                                                         topic).replace(
            '{{join_url}}', join_url)
    if summary and not record:
        html = get_html_with_summary_without_recordings()
        text = get_txt_with_summary_without_recordings()
        texthtml = html.replace('{{sig_name}}', sig_name).replace('{{start_time}}', start_time).replace('{{topic}}',
                                                                                                        topic).replace(
            '{{join_url}}', join_url).replace('{{summary}}', summary)
        textplain = text.replace('{{sig_name}}', sig_name).replace('{{start_time}}', start_time).replace('{{topic}}',
                                                                                                         topic).replace(
            '{{join_url}}', join_url).replace('{{summary}}', summary)
    if not summary and record:
        html = get_html_without_summary_with_recordings()
        text = get_txt_without_summary_with_recordings()
        texthtml = html.replace('{{sig_name}}', sig_name).replace('{{start_time}}', start_time).replace('{{topic}}',
                                                                                                        topic).replace(
            '{{join_url}}', join_url)
        textplain = text.replace('{{sig_name}}', sig_name).replace('{{start_time}}', start_time).replace('{{topic}}',
                                                                                                         topic).replace(
            '{{join_url}}', join_url)
    if summary and record:
        html = get_html_with_summary_with_recordings()
        text = get_txt_with_summary_with_recordings()
        texthtml = html.replace('{{sig_name}}', sig_name).replace('{{start_time}}', start_time).replace('{{topic}}',
                                                                                                        topic).replace(
            '{{join_url}}', join_url).replace('{{summary}}', summary)
        textplain = text.replace('{{sig_name}}', sig_name).replace('{{start_time}}', start_time).replace('{{topic}}',
                                                                                                         topic).replace(
            '{{join_url}}', join_url).replace('{{summary}}', summary)

    with open('templates/images.yaml', 'r') as f:
        images = yaml.load(f.read(), Loader=yaml.Loader)['images']
    if len(images) < 3:
        return
    random.shuffle(images)
    h1 = images[0]['href']
    s1 = images[0]['src']
    h2 = images[1]['href']
    s2 = images[1]['src']
    h3 = images[2]['href']
    s3 = images[2]['src']

    texthtml = texthtml.replace('{{sig_name}}', sig_name).replace('{{start_time}}', start_time).replace('{{topic}}',
                                                                                                        topic).replace(
        '{{join_url}}', join_url).replace('{{h1}}', h1).replace('{{s1}}', s1).replace('{{h2}}', h2).replace('{{s2}}',
                                                                                                            s2).replace(
        '{{h3}}', h3).replace('{{s3}}', s3)

    for i in [s1, s2, s3]:
        f = open(os.path.join('templates', 'images', 'activities', i), 'rb')
        msgImage = MIMEImage(f.read())
        f.close()
        msgImage.add_header('Content-ID', os.path.join('templates', 'images', 'activities', i))
        msg.attach(msgImage)

    f = open('templates/images/foot.png', 'rb')
    msgImage = MIMEImage(f.read())
    f.close()
    msgImage.add_header('Content-ID', 'templates/images/foot.png')
    msg.attach(msgImage)

    alternative.attach(MIMEText(textplain, 'plain', 'utf-8'))
    alternative.attach(MIMEText(texthtml, 'html', 'utf-8'))
    msg.attach(alternative)

    msg['Subject'] = topic
    msg['From'] = 'openEuler conference'
    msg['To'] = toaddrs_string

    try:
        gmail_username = settings.GMAIL_USERNAME
        gmail_password = settings.GMAIL_PASSWORD
        server = smtplib.SMTP(settings.SMTP_SERVER_HOST, settings.SMTP_SERVER_PORT)
        server.ehlo()
        server.starttls()
        server.login(gmail_username, gmail_password)
        server.sendmail(gmail_username, toaddrs_list, msg.as_string())
        logger.info('email string: {}'.format(toaddrs))
        logger.info('error addrs: {}'.format(error_addrs))
        logger.info('email sent: {}'.format(toaddrs_string))
        server.quit()
    except smtplib.SMTPException as e:
        logger.error(e)
