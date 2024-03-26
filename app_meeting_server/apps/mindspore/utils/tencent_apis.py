import base64
import json
import logging
import requests
from app_meeting_server.utils.tencent_apis import get_signature, get_url
from mindspore.models import Meeting

logger = logging.getLogger('log')


def cancelMeeting(mid):
    meeting = Meeting.objects.get(mid=mid)
    host_id = meeting.host_id
    mmid = meeting.mmid
    payload = json.dumps({
        "userid": host_id,
        "instanceid": 1,
        "reason_code": 1
    })
    uri = '/v1/meetings/{}/cancel'.format(mmid)
    url = get_url(uri)
    signature, headers = get_signature('POST', uri, payload)
    r = requests.post(url, headers=headers, data=payload)
    if r.status_code != 200:
        logger.error('Fail to cancel meeting {}'.format(mid))
        logger.error(r.json())
        return r.status_code
    logger.info('Cancel meeting {}'.format(mid))
    return r.status_code


def getParticipants(mid):
    meeting = Meeting.objects.get(mid=mid)
    mmid = meeting.mmid
    host_id = meeting.host_id
    uri = '/v1/meetings/{}/participants?userid={}'.format(mmid, host_id)
    url = get_url(uri)
    signature, headers = get_signature('GET', uri, "")
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        res = {
            'total_records': r.json()['total_count'],
            'participants': [{'name': base64.b64decode(x['user_name'].encode()).decode()} for x in r.json()['participants']]
        }
        return r.status_code, res
    return r.status_code, r.json()
