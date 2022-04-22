import datetime
import logging
import json
import requests
import subprocess
import time
from django.conf import settings
from meetings.models import Meeting

logger = logging.getLogger('log')


def createProxyToken(host_id):
    """获取代理鉴权token"""
    host_dict = settings.WELINK_HOSTS
    if host_id not in host_dict.keys():
        logger.error('host_id {} is invalid'.format(host_id))
        return None
    account = host_dict[host_id]['account']
    pwd = host_dict[host_id]['pwd']
    url = 'https://api.meeting.huaweicloud.com/v1/usg/acs/auth/proxy'
    headers = {
        'Content-Type': 'application/json; charset=UTF-8'
    }
    payload = {
        'authServerType': 'workplace',
        'authType': 'AccountAndPwd',
        'clientType': 72,
        'account': account,
        'pwd': pwd
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code != 200:
        logger.error('Fail to get proxy token, status_code: {}'.format(response.status_code))
        return None
    return response.json()['accessToken']


def createMeeting(date, start, end, topic, host, record):
    """预定会议"""
    access_token = createProxyToken(host)
    startTime = date + ' ' + start
    length = int((datetime.datetime.strptime(end, '%H:%M') - datetime.datetime.strptime(start, '%H:%M')).seconds / 60)
    url = 'https://api.meeting.huaweicloud.com/v1/mmc/management/conferences'
    headers = {
        'Content-Type': 'application/json',
        'X-Access-Token': access_token
    }
    data = {
        'startTime': startTime,
        'length': length,
        'subject': topic,
        'mediaTypes': 'HDVideo',
        'confConfigInfo': {
            'isAutoMute': True,
            'isHardTerminalAutoMute': True,
            'isGuestFreePwd': True,
            'allowGuestStartConf': True
        }
    }
    if record == 'cloud':
        data['isAutoRecord'] = True
        data['recordType'] = True
    response = requests.post(url, headers=headers, data=json.dumps(data))
    resp_dict = {}
    if response.status_code != 200:
        logger.error('Fail to create meeting, status_code is {}'.format(response.status_code))
        return response.status_code, resp_dict
    resp_dict['mid'] = response.json()[0]['conferenceID']
    resp_dict['start_url'] = response.json()[0]['chairJoinUri']
    resp_dict['join_url'] = response.json()[0]['guestJoinUri']
    resp_dict['host_id'] = response.json()[0]['userUUID']
    return response.status_code, resp_dict


def cancelMeeting(mid, host_id):
    """取消会议"""
    access_token = createProxyToken(host_id)
    url = 'https://api.meeting.huaweicloud.com/v1/mmc/management/conferences'
    headers = {
        'X-Access-Token': access_token
    }
    params = {
        'conferenceID': mid,
        'type': 1
    }
    response = requests.delete(url, headers=headers, params=params)
    if response.status_code != 200:
        logger.error('Fail to cancel meeting {}'.format(mid))
        logger.error(response.json())
        return response.status_code
    logger.info('Cancel meeting {}'.format(mid))
    return response.status_code


def listHisMeetings(host_id):
    """获取历史会议列表"""
    access_token = createProxyToken(host_id)
    tn = int(time.time())
    endDate = tn * 1000
    startDate = (tn - 3600 * 24) * 1000
    url = 'https://api.meeting.huaweicloud.com/v1/mmc/management/conferences/history'
    headers = {
        'X-Access-Token': access_token
    }
    params = {
        'startDate': startDate,
        'endDate': endDate,
        'limit': 500
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        logger.error('Fail to get history meetings list')
        logger.error(response.json())
        return {}
    return response.json()


def getParticipants(mid):
    """获取会议参会者"""
    meeting = Meeting.objects.get(mid=mid)
    host_id = meeting.host_id
    access_token = createProxyToken(host_id)
    headers = {
        'X-Access-Token': access_token
    }
    url = 'https://api.meeting.huaweicloud.com/v1/mmc/management/conferences/history/confAttendeeRecord'
    meetings_lst = listHisMeetings(host_id)
    meetings_data = meetings_lst.get('data')
    conf_uuid = None
    for item in meetings_data:
        if item['conferenceID'] == str(mid):
            conf_uuid = item['confUUID']
            break
    params = {
        'confUUID': conf_uuid,
        'limit': 500
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        resp = {
            'total_records': response.json()['count'],
            'participants': response.json()['data']
        }
        return response.status_code, resp
    logger.error('Fail to get participants of meeting {}'.format(mid))
    logger.error(response.json())
    return response.status_code, response.json()

