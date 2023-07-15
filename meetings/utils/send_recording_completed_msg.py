import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.conf import settings

logger = logging.getLogger('log')


def sendmail(topic, group_name, date, start, end, meeting_code, download_url):
    toaddrs = settings.RECORDING_RECEIVER
    toaddrs_list = toaddrs.split(',')
    # 构造邮件
    msg = MIMEMultipart()
    # 添加邮件主体
    with open('templates/template_recording_completed.html') as fp:
        body = fp.read()
        body_of_email = body.replace('{{topic}}', topic).replace('{{group_name}}', group_name).replace('{{date}}',
                                                                                                       date).replace(
            '{{start}}', start).replace('{{end}}', end).replace('{{meeting_code}}', meeting_code).replace(
            '{{download_url}}', download_url)
    content = MIMEText(body_of_email, 'html', 'utf-8')
    msg.attach(content)
    sender = os.getenv('SMTP_SENDER', '')
    msg['Subject'] = 'MindSporeApp录像生成'
    msg['From'] = 'MindSpore App'
    msg['To'] = toaddrs
    # 登录服务器发送邮件
    try:
        gmail_username = settings.GMAIL_USERNAME
        gmail_password = settings.GMAIL_PASSWORD
        server = smtplib.SMTP(settings.SMTP_SERVER_HOST, settings.SMTP_SERVER_PORT)
        server.ehlo()
        server.starttls()
        server.login(gmail_username, gmail_password)
        server.sendmail(sender, toaddrs_list, msg.as_string())
        logger.info('email sent: {}'.format(toaddrs_list))
        server.quit()
    except smtplib.SMTPException as e:
        logger.error(e)
