# -*- coding: utf-8 -*-
# @Time    : 2023/10/25 11:12
# @Author  : Tom_zc
# @FileName: check_params.py
# @Software: PyCharm
import datetime
from app_meeting_server.utils.regular_match import match_email


def check_email_list(email_list_str):
    # len of email list str gt 600 and the single email limit 30 and limit 20 email
    err_msgs = list()
    if len(email_list_str) > 600:
        msg = "The length of email_list is gt 600"
        err_msgs.append(msg)
    email_list = email_list_str.split(";")
    for email in email_list:
        if len(email) > 30:
            msg = "The length of email is gt 30"
            err_msgs.append(msg)
        if not match_email(email):
            msg = "The email does not conform to the format"
            err_msgs.append(msg)
    return err_msgs


def check_duration(start, end, date, now_time):
    err_msg = list()
    start_time = datetime.datetime.strptime(' '.join([date, start]), '%Y-%m-%d %H:%M')
    end_time = datetime.datetime.strptime(' '.join([date, end]), '%Y-%m-%d %H:%M')
    if start_time <= now_time:
        err_msg.append('The start time should not be later than the current time')
    if (start_time - now_time).days > 60:
        err_msg.append('The start time is at most 60 days later than the current time')
    if start_time >= end_time:
        err_msg.append('The start time should not be later than the end time')
    return err_msg
