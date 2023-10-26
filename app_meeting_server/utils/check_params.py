# -*- coding: utf-8 -*-
# @Time    : 2023/10/25 11:12
# @Author  : Tom_zc
# @FileName: check_params.py
# @Software: PyCharm
import datetime
import logging
from django.db import models
from app_meeting_server.utils.regular_match import match_email
from app_meeting_server.utils.ret_api import MyValidationError

logger = logging.getLogger('log')


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


def check_group_id(group_model, value):
    if not issubclass(group_model, models.Model):
        raise MyValidationError('Internal Error')
    if group_model.objects.filter(id=value).count() == 0:
        raise MyValidationError('The Group is not exist')
    try:
        value = int(value)
    except Exception as e:
        logger.error("[check_group_id]:{}".format(e))
        raise MyValidationError('Invalid Parameters')
    return value


def check_user_ids(value):
    new_list_ids = list()
    try:
        list_ids = value.split('-')
        if len(list_ids) > 50:
            raise Exception("The max len of list_ids gt 50")
        if len(list_ids) <= 0:
            raise Exception("The max len of list_ids le 50")
        for user_id in list_ids:
            new_user_id = int(user_id)
            new_list_ids.append(new_user_id)
    except Exception as e:
        msg = 'Invalid input.The ids should be like "1-2-3", or the length of id gt 50'
        logger.error("msg:{}, err:{}".format(msg, e))
        raise MyValidationError(msg)
    return new_list_ids


def check_group_user(group_user_model, group_id, user_ids):
    if not issubclass(group_user_model, models.Model):
        raise MyValidationError('Internal Error')
    if len(user_ids) != group_user_model.objects.filter(group_id=group_id, user_id__in=user_ids).count():
        raise MyValidationError('Invalid Parameter')


def check_group_id_and_user_ids(group_id, user_ids, group_user_model,  group_model):
    group_id = check_group_id(group_model, group_id)
    new_list_ids = check_user_ids(user_ids)
    check_group_user(group_user_model, group_id, new_list_ids)
    return group_id, new_list_ids


