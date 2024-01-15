import datetime
import logging
import json
import requests
from app_meeting_server.utils.welink_apis import createProxyToken, get_url, listHisMeetings
from opengauss.models import Meeting

logger = logging.getLogger('log')


def updateMeeting(mid, date, start, end, topic, record):
    host = Meeting.objects.get(mid=mid).host_id
    access_token = createProxyToken(host)
    startTime = (datetime.datetime.strptime(date + start, '%Y-%m-%d%H:%M') - datetime.timedelta(hours=8)).strftime(
        '%Y-%m-%d %H:%M')
    length = int((datetime.datetime.strptime(end, '%H:%M') - datetime.datetime.strptime(start, '%H:%M')).seconds / 60)
    uri = '/v1/mmc/management/conferences'
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
    params = {'conferenceID': mid}
    if record == 'cloud':
        data['isAutoRecord'] = 1
        data['recordType'] = 2
    response = requests.put(get_url(uri), params=params, headers=headers, data=json.dumps(data))
    return response.status_code


def getParticipants(mid):
    """获取会议参会者"""
    meeting = Meeting.objects.get(mid=mid)
    host_id = meeting.host_id
    access_token = createProxyToken(host_id)
    headers = {
        'X-Access-Token': access_token
    }
    uri = '/v1/mmc/management/conferences/history/confAttendeeRecord'
    meetings_lst = listHisMeetings(host_id)
    meetings_data = meetings_lst.get('data')
    participants = {
        'total_records': 0,
        'participants': []
    }
    status = 200
    for item in meetings_data:
        if item['conferenceID'] == str(mid):
            conf_uuid = item['confUUID']
            params = {
                'confUUID': conf_uuid,
                'limit': 500
            }
            response = requests.get(get_url(uri), headers=headers, params=params)
            if response.status_code == 200:
                participants['total_records'] += response.json()['count']
                for participant_info in response.json()['data']:
                    participants['participants'].append(participant_info)
            else:
                status = response.status_code
                participants = response.json()
                break
    return status, participants
