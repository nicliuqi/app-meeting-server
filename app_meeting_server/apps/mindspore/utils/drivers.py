from mindspore.models import Meeting
from app_meeting_server.utils import tencent_apis, welink_apis
from mindspore.utils import tencent_apis as mta
from mindspore.utils import welink_apis as mwa


def createMeeting(platform, date, start, end, topic, host, record):
    status, content = (None, None)
    if platform == 'tencent':
        status, content = tencent_apis.createMeeting(date, start, end, topic, host, record)
    elif platform == 'welink':
        status, content = welink_apis.createMeeting(date, start, end, topic, host, record)
    return status, content


def cancelMeeting(mid):
    meeting = Meeting.objects.get(mid=mid)
    mplatform = meeting.mplatform
    host_id = meeting.host_id
    status = None
    if mplatform == 'tencent':
        status = mta.cancelMeeting(mid)
    elif mplatform == 'welink':
        status = welink_apis.cancelMeeting(mid, host_id)
    return status


def getParticipants(mid):
    meeting = Meeting.objects.get(mid=mid)
    mplatform = meeting.mplatform
    status, res = (None, None)
    if mplatform == 'tencent':
        status, res = mta.getParticipants(mid)
    elif mplatform == 'welink':
        status, res = mwa.getParticipants(mid)
    return status, res
