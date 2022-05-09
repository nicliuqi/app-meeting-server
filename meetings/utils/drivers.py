from meetings.models import Meeting
from meetings.utils import tecent_apis, welink_apis


def createMeeting(platform, date, start, end, topic, host, record):
    status, content = (None, None)
    if platform == 'tencent':
        status, content = tecent_apis.createMeeting(date, start, end, topic, host, record)
    elif platform == 'welink':
        status, content = welink_apis.createMeeting(date, start, end, topic, host, record)
    return status, content


def cancelMeeting(mid):
    meeting = Meeting.objects.get(mid=mid)
    mplatform = meeting.mplatform
    host_id = meeting.host_id
    status = None
    if mplatform == 'tencent':
        status = tecent_apis.cancelMeeting(mid)
    elif mplatform == 'welink':
        status = welink_apis.cancelMeeting(mid, host_id)
    return status


def getParticipants(mid):
    meeting = Meeting.objects.get(mid=mid)
    mplatform = meeting.mplatform
    status, res = (None, None)
    if mplatform == 'tencent':
        status, res = tecent_apis.getParticipants(mid)
    elif mplatform == 'welink':
        status, res = welink_apis.getParticipants(mid)
    return status, res
