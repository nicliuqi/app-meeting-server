import logging
import requests
from openeuler.models import Meeting
from app_meeting_server.utils.welink_apis import createProxyToken, get_url, listHisMeetings

logger = logging.getLogger('log')


def getParticipants(mid):
    """获取会议参会者"""
    meeting = Meeting.objects.get(mid=mid)
    host_id = meeting.host_id
    access_token = createProxyToken(host_id)
    if not access_token:
        return 400, {}
    headers = {
        'X-Access-Token': access_token
    }
    uri = '/v1/mmc/management/conferences/history/confAttendeeRecord'
    meetings_lst = listHisMeetings(meeting)
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
