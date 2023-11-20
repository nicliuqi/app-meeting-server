# -*- coding: utf-8 -*-
# @Time    : 2023/10/25 11:12
# @Author  : Tom_zc
# @FileName: check_params.py
# @Software: PyCharm
import datetime
import json
import logging
import html
from django.db import models
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from django.utils.translation import ugettext_lazy as _
from app_meeting_server.utils.common import make_refresh_signature
from app_meeting_server.utils.regular_match import match_email, match_url, match_crlf
from app_meeting_server.utils.ret_api import MyValidationError
from app_meeting_server.utils.ret_code import RetCode
from django.contrib.auth import get_user_model

logger = logging.getLogger('log')


def check_none(value):
    if not value:
        logger.error("invalid:{}".format(value))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)


def check_int(value):
    try:
        return int(value)
    except Exception as e:
        logger.error("invalid int:{}, and e:{}".format(value, e))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)


def check_float(value):
    try:
        return float(value)
    except Exception as e:
        logger.error("invalid float:{}, and e:{}".format(value, e))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)


def check_itude(value):
    try:
        value = str(value)
        value_list = value.split(".")
        if len(value_list) > 2:
            raise Exception("multiple decimal points")
        elif len(value_list) == 2 and len(str(value_list[1])) > 5:
            raise Exception("decimal_places max is 2 bit")
        elif len(value) > 9:
            raise Exception("length over 9 bit")
        return float(value)
    except Exception as e:
        logger.error("invalid float:{}, and e:{}".format(value, e))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)


def check_refresh_token(refresh):
    if not refresh:
        logger.error("receive empty refresh")
        raise AuthenticationFailed(_('lack of refresh'))
    try:
        RefreshToken(refresh, verify=True)
    except Exception as e:
        logger.error("invalid refresh_token:{}".format(e))
        raise AuthenticationFailed(_("Token is invalid or expired"))
    refresh_signature = make_refresh_signature(refresh)
    user_model = get_user_model()
    cur_user = user_model.objects.filter(refresh_signature=refresh_signature).first()
    if cur_user is None:
        logger.error("refresh doesnt match")
        raise AuthenticationFailed(_('invalid refresh'))
    return cur_user


def check_invalid_content(content, check_crlf=True):
    # check xss and url, and \r\n
    # 1.check xss
    content = content.strip()
    text = html.escape(content, quote=True)
    if len(text) != len(content):
        logger.error("check xss:{}".format(content))
        raise MyValidationError(RetCode.STATUS_START_VALID_XSS)
    # 2.check url
    reg = match_url(content)
    if reg:
        logger.error("check invalid url:{}".format(",".join(reg)))
        raise MyValidationError(RetCode.STATUS_START_VALID_URL)
    # 3.check \r\n
    if check_crlf:
        reg = match_crlf(content)
        if reg:
            logger.error("check crlf url:{}".format(",".join(reg)))
            raise MyValidationError(RetCode.STATUS_START_VALID_CRLF)


def check_field(field, field_bit):
    if not field or len(field) == 0 or len(field) > field_bit:
        logger.error("check invalid field({}) over bit({})".format(str(field), str(field_bit)))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)


def check_type(type_str):
    if type_str not in ["all", "meetings", "activity", "summit"]:
        logger.error("check invalid type:{}".format(type_str))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)


def check_date(date_str):
    try:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d')
    except Exception as e:
        logger.error("invalid date:{}, and e:{}".format(date_str, str(e)))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)


def check_time(time_str, is_meetings=False, is_activity=False):
    """
        time_str is 08:00   08 in 08-11 00 in 00-60 and
        meetings minute is in [0,15,30,45] and activity is in [0,5,10,15,20,25,30,35,40,45,50,55]
    """
    # time_str is 08:00   08 in 08-11 00 in 00-60
    date_list = time_str.split(":")
    hours_int = int(date_list[0])
    minute_int = int(date_list[1])
    if hours_int < 8 or hours_int > 22:
        logger.error("hours {} must in 8-22".format(str(hours_int)))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    if minute_int < 0 or minute_int > 59:
        logger.error("minute {} must in 0:59".format(str(hours_int)))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    if is_meetings:
        if minute_int not in [0, 15, 30, 45]:
            logger.error("minute {} must in [0, 15, 30, 45]".format(str(minute_int)))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    elif is_activity:
        if minute_int not in [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]:
            logger.error("minute {} must in [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]".format(str(minute_int)))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)


def check_schedules(schedules_list):
    for schedules in schedules_list:
        start = schedules["start"]
        end = schedules["end"]
        check_time(start, is_activity=True)
        check_time(end, is_activity=True)
        topic = schedules["topic"]
        check_invalid_content(topic)
        for speakers in schedules["speakerList"]:
            name = speakers["name"]
            check_invalid_content(name)
            title = speakers.get("title")
            if title:
                check_invalid_content(title)


def check_email_list(email_list_str):
    # len of email list str gt 1000 and the single email limit 50 and limit 20 email
    if len(email_list_str) > 1020:
        logger.error("The length of email_list is gt 1000")
        raise MyValidationError(RetCode.STATUS_MEETING_EMAIL_LIST_OVER_LIMIT)
    email_list = email_list_str.split(";")
    for email in email_list:
        if len(email) > 50:
            logger.error("The length of email is gt 50")
            raise MyValidationError(RetCode.STATUS_MEETING_EMAIL_OVER_LIMIT)
        if email and not match_email(email):
            logger.error("The email does not conform to the format")
            raise MyValidationError(RetCode.STATUS_MEETING_INVALID_EMAIL)


def check_duration(start, end, date, now_time, is_meetings=False, is_activity=False):
    err_msg = list()
    check_time(start, is_meetings=is_meetings, is_activity=is_activity)
    check_time(end, is_meetings=is_meetings, is_activity=is_activity)
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
    try:
        value = int(value)
    except Exception as e:
        logger.error("[check_group_id]:{}".format(e))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    if group_model.objects.filter(id=value).count() == 0:
        raise MyValidationError(RetCode.STATUS_SIG_GROUP_NOT_EXIST)
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


def check_group_id_and_user_ids(group_id, user_ids, group_user_model, group_model):
    group_id = check_group_id(group_model, group_id)
    new_list_ids = check_user_ids(user_ids)
    check_group_user(group_user_model, group_id, new_list_ids)
    return group_id, new_list_ids


def check_meetings_params(request, group_model):
    data = request.data
    now_time = datetime.datetime.now()
    topic = data.get('topic')
    platform = data.get('platform', 'zoom')
    sponsor = data.get('sponsor')
    date = data.get('date')
    start = data.get('start')
    end = data.get('end')
    group_id = data.get('group_id')
    group_name = data.get('group_name')
    emaillist = data.get('emaillist', '')
    community = data.get('community', 'openeuler')
    summary = data.get('agenda')
    record = data.get('record')
    etherpad = data.get('etherpad')
    # 0 check group_id
    group_id = check_int(group_id)
    # 1.check topic
    check_field(topic, 128)
    check_invalid_content(topic)
    # 2.check platform
    if not isinstance(platform, str):
        logger.error("Field platform/{} must be string type".format(platform))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    else:
        host_dict = settings.MEETING_HOSTS.get(platform.lower())
        if not host_dict or not isinstance(host_dict, dict):
            logger.error("Could not match any meeting host")
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    # 3.check sponsor
    check_field(sponsor, 20)
    check_invalid_content(sponsor)
    # 4.check start,end,date
    try:
        check_duration(start, end, date, now_time, is_meetings=True)
    except ValueError:
        logger.error('Invalid start time or end time')
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    # 5. check group
    groups_obj = group_model.objects.filter(group_name=group_name, id=group_id)
    if groups_obj.count() == 0:
        logger.error('Invalid group name: {}'.format(group_name))
        raise MyValidationError(RetCode.STATUS_SIG_GROUP_NOT_EXIST)
    # 6. check etherpad
    check_field(etherpad, 64)
    if not etherpad.startswith(settings.ETHERPAD_PREFIX):
        logger.error('Invalid etherpad address {}'.format(str(etherpad)))
        raise MyValidationError(RetCode.STATUS_MEETING_INVALID_ETHERPAD)
    # 7.check community
    if community != settings.COMMUNITY.lower():
        logger.error('The field community must be the same as configure')
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    # 8.check agenda
    if summary:
        check_field(summary, 4096)
        check_invalid_content(summary, check_crlf=False)
    # 9.check record:
    if record not in ["cloud", ""]:
        logger.error('The invalid cloud:{}'.format(str(record)))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    # 10.check_email_list
    if emaillist:
        check_email_list(emaillist)
    validated_data = {
        'platform': platform,
        'host_dict': host_dict,
        'date': date,
        'start': start,
        'end': end,
        'topic': topic,
        'sponsor': sponsor,
        'group_name': group_name,
        'etherpad': etherpad,
        'community': community,
        'emaillist': emaillist,
        'summary': summary,
        'record': record,
        'user_id': request.user.id,
        'group_id': group_id
    }
    return validated_data


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
    # 1.check title
    check_field(title, 50)
    check_invalid_content(title)
    # 2.check activity_type
    activity_type = check_int(activity_type)
    if activity_type not in [offline, online]:
        logger.error('Invalid activity type: {}'.format(activity_type))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    # 3.check date
    try:
        if date <= datetime.datetime.strftime(now_time, '%Y-%m-%d'):
            logger.error('The start date {} should be earlier than tomorrow'.format(str(date)))
            raise MyValidationError(RetCode.STATUS_ACTIVITY_DATA_GT_NOW)
        if activity_type == online:
            check_duration(start, end, date, now_time, is_activity=True)
    except ValueError:
        logger.error('Invalid datetime params {}'.format(date))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    # 4.check poster
    poster = check_int(poster)
    if poster not in range(1, 5):
        logger.error('Invalid poster: {}'.format(poster))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    # 5.check register_url
    if not register_url.startswith('https://'):
        logger.error('Invalid register url: {}'.format(register_url))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
    # 6.check synopsis
    if synopsis:
        check_field(synopsis, 4096)
        check_invalid_content(synopsis, check_crlf=False)
    # 7.check address in offline
    if activity_type == offline:
        longitude = check_itude(longitude)
        latitude = check_itude(latitude)
        check_field(address, 100)
        check_invalid_content(address)
        check_field(detail_address, 100)
        check_invalid_content(detail_address)
    # 8.check schedules
    check_schedules(schedules)
    schedules_str = json.dumps(schedules)
    check_field(schedules_str, 8192)
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


def check_schedules_string(content):
    try:
        schedules_obj = json.loads(content)
        check_schedules(schedules_obj)
    except Exception as e:
        logger.error("[check_schedules_string] {}".format(e))
        raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
