import logging
import smtplib
from django.conf import settings
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from .email_templates import feedback_email_template, reply_email_template

logger = logging.getLogger('log')


def run(feedback_type, feedback_email, feedback_content):
    msg = MIMEMultipart()
    body_of_email = feedback_email_template(feedback_type, feedback_email, feedback_content)
    content = MIMEText(body_of_email, 'html', 'utf-8')
    msg.attach(content)
    reply_msg = MIMEMultipart()
    reply_body_of_email = reply_email_template()
    reply_content = MIMEText(reply_body_of_email, 'html', 'utf-8')
    reply_msg.attach(reply_content)

    # 完善邮件信息
    mailto = 'contact@mindspore.cn'
    msg['Subject'] = 'MindSpore小程序意见反馈'
    msg['From'] = 'MindSpore MiniProgram'
    msg['To'] = mailto
    reply_msg['Subject'] = 'MindSpore小程序意见反馈'
    reply_msg['From'] = 'MindSpore MiniProgram'
    reply_msg['To'] = feedback_email

    # 登录服务器发送邮件
    try:
        gmail_username = settings.GMAIL_USERNAME
        gmail_password = settings.GMAIL_PASSWORD
        sender = 'public@mindspore.cn'
        server = smtplib.SMTP(settings.SMTP_SERVER_HOST, settings.SMTP_SERVER_PORT)
        server.ehlo()
        server.starttls()
        server.login(gmail_username, gmail_password)
        server.sendmail(sender, mailto.split(','), msg.as_string())
        logger.info('小程序回复邮件发送成功')
        server.sendmail(sender, feedback_email.split(','), reply_msg.as_string())
        logger.info('小程序反馈邮件发送成功')
        server.quit()
    except smtplib.SMTPException as e:
        logger.error(e)
