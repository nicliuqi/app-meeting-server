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
from app_meeting_server.utils.ret_code import RetCode

logger = logging.getLogger('log')


def check_email_list(email_list_str):
    # len of email list str gt 600 and the single email limit 30 and limit 20 email
    if len(email_list_str) > 600:
        logger.error("The length of email_list is gt 600")
        raise MyValidationError(RetCode.STATUS_MEETING_EMAIL_LIST_OVER_LIMIT)
    email_list = email_list_str.split(";")
    for email in email_list:
        if len(email) > 30:
            logger.error("The length of email is gt 30")
            raise MyValidationError(RetCode.STATUS_MEETING_EMAIL_OVER_LIMIT)
        if email and not match_email(email):
            logger.error("The email does not conform to the format")
            raise MyValidationError(RetCode.STATUS_MEETING_INVALID_EMAIL)


def check_duration(start, end, date, now_time):
    err_msg = list()
    start_time = datetime.datetime.strptime(' '.join([date, start]), '%Y-%m-%d %H:%M')
    end_time = datetime.datetime.strptime(' '.join([date, end]), '%Y-%m-%d %H:%M')
    if start_time <= now_time:
        logger.error('The start time {} should not be later than the current time'.format(str(start)))
        raise MyValidationError(RetCode.STATUS_START_GT_NOW)
    if (start_time - now_time).days > 60:
        logger.error('The start time {} is at most 60 days later than the current time'.format(str(start)))
        raise MyValidationError(RetCode.STATUS_START_LT_LIMIT)
    if start_time >= end_time:
        logger.error('The start time {} should not be later than the end time {}'.format(str(start), str(end)))
        raise MyValidationError(RetCode.STATUS_START_LT_END)
    return err_msg


def check_group_id(group_model, value):
    if not issubclass(group_model, models.Model):
        raise MyValidationError(RetCode.INTERNAL_ERROR)
    if group_model.objects.filter(id=value).count() == 0:
        raise MyValidationError(RetCode.STATUS_SIG_GROUP_NOT_EXIST)
    try:
        value = int(value)
    except Exception as e:
        logger.error("[check_group_id]:{}".format(e))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
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
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    return new_list_ids


def check_group_user(group_user_model, group_id, user_ids):
    if not issubclass(group_user_model, models.Model):
        raise MyValidationError(RetCode.INTERNAL_ERROR)
    if len(user_ids) != group_user_model.objects.filter(group_id=group_id, user_id__in=user_ids).count():
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)


def check_group_id_and_user_ids(group_id, user_ids, group_user_model,  group_model):
    group_id = check_group_id(group_model, group_id)
    new_list_ids = check_user_ids(user_ids)
    check_group_user(group_user_model, group_id, new_list_ids)
    return group_id, new_list_ids


def check_activity_params(data, online, offline):
    now_time = datetime.datetime.now()
    title = data.get('title')
    date = data.get('date')
    activity_type = data.get('activity_type')
    synopsis = data.get('synopsis')
    poster = data.get('poster')
    register_url = data.get('register_url')
    address = data.get('address')
    detail_address = data.get('detail_address')
    longitude = data.get('longitude')
    latitude = data.get('latitude')
    start = data.get('start')
    end = data.get('end')
    schedules = data.get('schedules')
    # todo 1.没有校验的参数有：synopsis， address, detail_address, longitude, latitude, schedules
    try:
        if date <= datetime.datetime.strftime(now_time, '%Y-%m-%d'):
            logger.error('The start date {} should be earlier than tomorrow'.format(str(date)))
            raise MyValidationError(RetCode.STATUS_ACTIVITY_DATA_GT_NOW)
        if activity_type == online:
            check_duration(start, end, date, now_time)
    except ValueError:
        logger.error('Invalid datetime params {}'.format(date))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    if not title:
        logger.error('Activity title could not be empty')
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    if activity_type not in [offline, online]:
        logger.error('Invalid activity type: {}'.format(activity_type))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    if poster not in range(1, 5):
        logger.error('Invalid poster: {}'.format(poster))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    if not register_url.startswith('https://'):
        logger.error('Invalid register url: {}'.format(register_url))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    validated_data = {
        'title': title,
        'date': date,
        'activity_type': activity_type,
        'synopsis': synopsis,
        'poster': poster,
        'register_url': register_url,
        'address': address,
        'detail_address': detail_address,
        'longitude': longitude,
        'latitude': latitude,
        'start': start,
        'end': end,
        'schedules': schedules
    }
    return validated_data


def check_more_activity_params(data):
    now_time = datetime.datetime.now()
    title = data.get('title')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    activity_category = data.get('activity_category')
    activity_type = data.get('activity_type')
    address = data.get('address')
    detail_address = data.get('detail_address')
    longitude = data.get('longitude')
    latitude = data.get('latitude')
    online_url = data.get('online_url')
    register_url = data.get('register_url')
    synopsis = data.get('synopsis')
    schedules = data.get('schedules')
    poster = data.get('post')
    try:
        if start_date <= datetime.datetime.strftime(now_time, '%Y-%m-%d'):
            logger.error('The start date should be earlier than tomorrow')
            raise MyValidationError(RetCode.STATUS_START_GT_NOW)
        start_time = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end_time = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        if (start_time - now_time).days > 60:
            logger.error('The start time is at most 60 days later than the current time')
            raise MyValidationError(RetCode.STATUS_START_LT_LIMIT)
        if start_time >= end_time:
            logger.error('The start time should not be later than the end time')
            raise MyValidationError(RetCode.STATUS_START_LT_END)
    except ValueError:
        logger.error('Invalid datetime params')
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    if not title:
        logger.error('Activity title could not be empty')
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    if activity_category not in range(1, 5):
        logger.error('Invalid activity category: {}'.format(activity_category))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    if activity_type not in range(1, 4):
        logger.error('Invalid activity type: {}'.format(activity_type))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    if not online_url.startswith('https://'):
        logger.error('Invalid online url: {}'.format(online_url))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    if not register_url.startswith('https://'):
        logger.error('Invalid register url: {}'.format(register_url))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    if poster not in range(1, 5):
        logger.error('Invalid poster: {}'.format(poster))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    validated_data = {
        'title': title,
        'start_date': start_date,
        'end_date': end_date,
        'activity_category': activity_category,
        'activity_type': activity_type,
        'address': address,
        'detail_address': detail_address,
        'longitude': longitude,
        'latitude': latitude,
        'online_url': online_url,
        'register_url': register_url,
        'synopsis': synopsis,
        'schedules': schedules,
        'poster': poster
    }
    return validated_data
