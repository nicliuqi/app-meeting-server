import datetime
import logging
import os
import stat

import requests
from django.apps import apps as django_apps
from django.db.models import Q
from django.conf import settings

from app_meeting_server.utils.bilibili_apis import Credential, sync, video_uploader
from app_meeting_server.utils.bilibili_apis.user import User
from app_meeting_server.utils.common import execute_cmd3, gen_new_temp_dir, make_dir
from app_meeting_server.utils.file_stream import download_big_file
from app_meeting_server.utils.html_template import cover_content
from app_meeting_server.utils import zoom_apis
from app_meeting_server.utils.obs_api import ObsClientImp
from app_meeting_server.utils.tencent_apis import get_records, get_video_download
from app_meeting_server.utils.welink_apis import listRecordings, getDetailDownloadUrl, downloadHWCloudRecording
from app_meeting_server.utils.zoom_apis import getOauthToken

logger = logging.getLogger('log')
Meeting = django_apps.get_model(settings.MEETING_MODEL)
Video = django_apps.get_model(settings.VIDEO_MODEL)
Record = django_apps.get_model(settings.RECORD_MODEL)


def search_target_meeting_ids():
    past_meetings = Meeting.objects.filter(is_delete=0).filter(
        Q(date__gt=str(datetime.datetime.now() - datetime.timedelta(days=7))) &
        Q(date__lte=datetime.datetime.now().strftime('%Y-%m-%d'))).values_list('mid', flat=True)
    return [x for x in past_meetings if x in list(Video.objects.filter(replay_url__isnull=True).values_list(
        'mid', flat=True))]


def is_archived(obs_server, bucket_name, object_key):
    search_res = obs_server.getObject(bucket_name, object_key)
    if not isinstance(search_res, dict):
        return False
    if search_res.get('status') != 200:
        return False
    return True


def generate_cover(meeting, filename):
    html_path = filename.replace('.mp4', '.html')
    image_path = filename.replace('.mp4', '.png')
    mid = meeting.mid
    topic = meeting.topic
    group_name = meeting.group_name
    date = meeting.date
    start = meeting.start
    end = meeting.end
    community = meeting.community
    content = cover_content(topic, group_name, date, start, end)
    flags = os.O_CREAT | os.O_WRONLY
    modes = stat.S_IWUSR | stat.S_IRUSR
    with os.fdopen(os.open(html_path, flags, modes), 'w') as f:
        f.write(content)
    if not os.path.exists(os.path.join(os.path.dirname(filename), 'cover.png')):
        execute_cmd3("cp app_meeting_server/static/{}/images/cover.png {}".format(community, os.path.dirname(filename)))
    execute_cmd3("wkhtmltoimage --enable-local-file-access {} {}".format(html_path, image_path))
    logger.info("meeting {}: generate cover".format(mid))
    return image_path


def get_bili_credential():
    return Credential(sessdata=settings.SESSDATA, bili_jct=settings.BILI_JCT)


def upload_to_bili(meeting_info, video_path, thumbnail_path):
    tag = meeting_info.get('tag')
    title = meeting_info.get('title')
    desc = meeting_info.get('desc')
    credential = get_bili_credential()
    page = video_uploader.VideoUploaderPage(path=video_path, title=title, description=desc)
    meta = {
        'copyright': 1,
        'desc': desc,
        'desc_format_id': 0,
        'dynamic': '',
        'interactive': 0,
        'no_reprint': 1,
        'subtitles': {
            'lan': '',
            'open': 0
        },
        'tag': tag,
        'tid': 124,
        'title': title
    }
    uploader = video_uploader.VideoUploader([page], meta, credential, cover=thumbnail_path)
    res = sync(uploader.start())
    return res


def get_obs_video_object(mid):
    if not Video.objects.filter(mid=mid):
        return
    meeting = Meeting.objects.get(mid=mid)
    date = meeting.date
    group_name = meeting.group_name
    community = meeting.community
    month = datetime.datetime.strptime(date, '%Y-%m-%d').strftime('%b').lower()
    return '{0}/{1}/{2}/{3}/{3}.mp4'.format(community, group_name, month, mid)


def get_obs_cover_object(video_object):
    return video_object.replace('.mp4', '.png')


def get_obs_video_download_url(bucket_name, obs_endpoint, video_object):
    return 'https://{}.{}/{}??response-content-disposition=attachment'.format(bucket_name, obs_endpoint, video_object)


def get_size_of_file(file_path):
    if not os.path.exists(file_path):
        logger.error('Could not get size of a non exist file: {}'.format(file_path))
        return
    return os.path.getsize(file_path)


def get_video_path(mid):
    dir_name = gen_new_temp_dir()
    make_dir(dir_name)
    target_name = mid + '.mp4'
    target_filename = os.path.join(dir_name, target_name)
    return target_filename


def generate_video_metadata(mid, video_object, video_path):
    meeting = Meeting.objects.get(mid=mid)
    date = meeting.date
    start = meeting.start
    end = meeting.end
    start_time = date + 'T' + start + ':00Z'
    end_time = date + 'T' + end + ':00Z'
    download_url = get_obs_video_download_url(settings.OBS_BUCKETNAME, settings.OBS_ENDPOINT, video_object)
    download_file_size = get_size_of_file(video_path)
    metadata = {
        "meeting_id": mid,
        "meeting_topic": meeting.topic,
        "community": meeting.community,
        "sig": meeting.group_name,
        "agenda": meeting.agenda,
        "record_start": start_time,
        "record_end": end_time,
        "download_url": download_url,
        "total_size": download_file_size,
        "attenders": []
    }
    return metadata


def upload_to_obs(obs_server, bucket_name, object_key, object_path, metadata=None):
    res = obs_server.uploadFile(bucketName=bucket_name, objectKey=object_key, uploadFile=object_path,
                                taskNum=10, enableCheckpoint=True, metadata=metadata)
    return res


def search_all_bili_videos():
    credential = get_bili_credential()
    user = User(settings.BILI_UID, credential)
    bvids = []
    pn = 1
    while True:
        res = sync(user.get_videos(pn=pn))
        if len(res.get('list').get('vlist')) == 0:
            break
        for video in res['list']['vlist']:
            bvid = video.get('bvid')
            if bvid not in bvids:
                bvids.append(bvid)
        pn += 1
    return bvids


def review_upload_results():
    logger.info('Start to review results for uploading videos to bili')
    bvids = search_all_bili_videos()
    waiting_update_mids = list(Record.objects.filter(url__isnull=True).values_list('mid', flat=True))
    for mid in waiting_update_mids:
        replay_url = Video.objects.get(mid=mid).replay_url
        if not replay_url:
            continue
        bvid = replay_url.split('/')[-1]
        if bvid not in bvids:
            logger.info('meeting {}: meeting video had not been passed, waiting...'.format(mid))
            continue
        logger.info('meeting {}: meeting video uploaded to bili passed which bvid is {}'.format(mid, replay_url))
        Record.objects.filter(mid=mid, platform='bilibili').update(url=replay_url)
    logger.info('review upload results ends')


def get_bili_replay_url(bvid):
    return settings.BILI_VIDEO_PREFIX + bvid


def get_zoom_recordings(meeting):
    mid = meeting.mid
    host_id = meeting.host_id
    uri = '/v2/users/{}/recordings'.format(host_id)
    token = getOauthToken()
    headers = {
        'authorization': 'Bearer {}'.format(token)
    }
    params = {
        'from': (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
        'page_size': 50
    }
    response = requests.get(zoom_apis.get_url(uri), headers=headers, params=params)
    if response.status_code != 200:
        logger.error('get recordings: {} {}'.format(response.status_code, response.json()['message']))
        return
    mids = [x['id'] for x in response.json()['meetings']]
    if mids.count(int(mid)) == 0:
        logger.info('meeting {}: no recordings yet'.format(mid))
        return
    if mids.count(int(mid)) == 1:
        record = list(filter(lambda x: x if x['id'] == int(mid) else None, response.json()['meetings']))[0]
        return record
    if mids.count(int(mid)) > 1:
        records = list(filter(lambda x: x if x['id'] == int(mid) else None, response.json()['meetings']))
        max_size = max([x['total_size'] for x in records])
        record = list(filter(lambda x: x if x['total_size'] == max_size else None, response.json()['meetings']))[0]
        return record


def get_zoom_recordings_download_url(meeting, recordings):
    mid = meeting.mid
    if not recordings:
        return
    recordings_list = list(filter(lambda x: x if x['file_extension'] == 'MP4' else None, recordings['recording_files']))
    if len(recordings_list) == 0:
        logger.info('meeting {}: recording'.format(mid))
        return
    if len(recordings_list) > 1:
        max_size = max([x['file_size'] for x in recordings_list])
        for recording in recordings_list:
            if recording['file_size'] != max_size:
                recordings_list.remove(recording)
    total_size = recordings_list[0]['file_size']
    logger.info('meeting {}: the full size of the recording file is {}'.format(mid, total_size))
    if total_size < settings.VIDEO_MINI_SIZE:
        logger.info('meeting {}: the file is too small to upload'.format(mid))
        return
    return recordings_list[0]['download_url']


def download_zoom_recording(meeting, download_url):
    mid = meeting.mid
    video_path = get_video_path(mid)
    r = requests.get(url=download_url, allow_redirects=False)
    url = r.headers['location']
    filename = download_big_file(url, video_path)
    return filename


def prepare_zoom_videos(meeting):
    recordings = get_zoom_recordings(meeting)
    download_url = get_zoom_recordings_download_url(meeting, recordings)
    video_path = download_zoom_recording(meeting, download_url)
    return video_path


def get_welink_recordings(meeting):
    mid = meeting.mid
    date = meeting.date
    start = meeting.start
    end = meeting.end
    start_time = date + ' ' + start
    end_time = date + ' ' + end
    host_id = meeting.host_id
    status, recordings = listRecordings(host_id)
    if status != 200:
        logger.info('Fail to get welink recordings')
        return []
    available_recordings = []
    if recordings['count'] == 0:
        return []
    recordings_data = recordings['data']
    start_order_set = set()
    for recording in recordings_data:
        confID = recording['confID']
        if confID != mid:
            continue
        startTime = (datetime.datetime.strptime(recording['startTime'], '%Y-%m-%d %H:%M') +
                     datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')
        rcdTime = recording['rcdTime']
        endTime = (datetime.datetime.strptime(startTime, '%Y-%m-%d %H:%M') + datetime.timedelta(seconds=rcdTime)). \
            strftime('%Y-%m-%d %H:%M')
        if endTime < start_time or startTime > end_time:
            continue
        start_order_set.add(startTime)
    for st in sorted(list(start_order_set)):
        for recording in recordings_data:
            confID = recording['confID']
            startTime = (datetime.datetime.strptime(recording['startTime'], '%Y-%m-%d %H:%M') +
                         datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')
            rcdTime = recording['rcdTime']
            if confID != mid:
                continue
            endTime = (datetime.datetime.strptime(startTime, '%Y-%m-%d %H:%M') + datetime.timedelta(seconds=rcdTime)). \
                strftime('%Y-%m-%d %H:%M')
            if endTime < start_time or startTime > end_time:
                continue
            if startTime == st:
                available_recordings.append(recording)
    return available_recordings


def get_welink_recordings_download_url_and_download(meeting, recordings):
    mid = meeting.mid
    if not recordings:
        logger.info('meeting {}: no available recordings'.format(mid))
        return
    waiting_download_recordings = []
    host_id = Meeting.objects.get(mid=mid).host_id
    for available_recording in recordings:
        conf_uuid = available_recording['confUUID']
        status, res = getDetailDownloadUrl(conf_uuid, host_id)
        record_urls = res['recordUrls'][0]['urls']
        for record_url in record_urls:
            if record_url['fileType'].lower() in ['hd', 'aux']:
                waiting_download_recordings.append(record_url)
    target_filename = get_video_path(mid)
    token = waiting_download_recordings[0]['token']
    download_url = waiting_download_recordings[0]['url']
    downloadHWCloudRecording(token, target_filename, download_url)
    return target_filename


def prepare_welink_videos(meeting):
    recordings = get_welink_recordings(meeting)
    return get_welink_recordings_download_url_and_download(meeting, recordings)


def get_tencent_recordings():
    return get_records()


def get_tencent_recordings_download_url_and_download(meeting, recordings):
    mid = meeting.mid
    if not recordings:
        logger.error("meeting {}: no available recordings".format(mid))
        return
    match_record = {}
    mmid = meeting.mmid
    date = meeting.date
    start = meeting.start
    start_time = ' '.join([date, start])
    start_timestamp = int(datetime.datetime.timestamp(datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M')))
    for record in recordings:
        if record.get('meeting_id') != mmid:
            continue
        if record.get('state') != 3:
            continue
        media_start_time = record.get('media_start_time')
        if abs(media_start_time // 1000 - start_timestamp) > 1800:
            continue
        record_file = record.get('record_files')[0]
        if record_file.get('record_size') < 1024 * 1024 * 10:
            continue
        if not match_record:
            match_record['record_file_id'] = record_file.get('record_file_id')
            match_record['record_size'] = record_file.get('record_size')
            match_record['userid'] = record.get('userid')
        else:
            if record_file.get('record_size') > match_record.get('record_size'):
                match_record['record_file_id'] = record_file.get('record_file_id')
                match_record['record_size'] = record_file.get('record_size')
                match_record['userid'] = record.get('userid')
    if not match_record:
        logger.info('Find no recordings about Tencent meeting which id is {}'.format(mid))
        return
    download_url = get_video_download(match_record.get('record_file_id'), match_record.get('userid'))
    if not download_url:
        logger.error("get empty url")
        return
    target_filename = get_video_path(mid)
    download_big_file(download_url, target_filename)
    return target_filename


def prepare_tencent_videos(meeting):
    recordings = get_tencent_recordings()
    return get_tencent_recordings_download_url_and_download(meeting, recordings)


def prepare_videos(meeting, platform):
    if platform == 'zoom':
        return prepare_zoom_videos(meeting)
    elif platform == 'welink':
        return prepare_welink_videos(meeting)
    elif platform == 'tencent':
        return prepare_tencent_videos(meeting)


def handle_recording(mid):
    logger.info('\nStart to handle recordings of meeting which mid is {}'.format(mid))
    # 1. get recordings of target meeting and download
    meeting = Meeting.objects.get(mid=mid)
    platform = meeting.mplatform
    video_path = prepare_videos(meeting, platform)
    if not video_path:
        logger.error('meeting {}: video path could not be empty'.format(mid))
        return
    if not os.path.exists(video_path):
        logger.error('meeting {}: fail to download video'.format(mid))
        return
    if os.path.getsize(video_path) == 0:
        logger.error('meeting {}: download but did not get the full video'.format(mid))
        return
    # 2. generate cover image
    cover_path = generate_cover(meeting, video_path)
    if not os.path.exists(cover_path):
        logger.error('meeting {}: fail to generate cover for meeting video'.format(mid))
        return
    # 3. upload video and cover to bili
    meeting_info = {
        'tag': '{}, SIG meeting, recording'.format(meeting.community),
        'title': '{}（{}）'.format(meeting.topic, meeting.date),
        'desc': 'community meeting recording for {}'.format(meeting.group_name)
    }
    res = upload_to_bili(meeting_info, video_path, cover_path)
    if not isinstance(res, dict) or 'bvid' not in res.keys():
        logger.error('Unexpected upload result to bili: {}'.format(res))
        return
    bvid = res.get('bvid')
    logger.info('meeting {}: upload to bili successfully, bvid is {}'.format(mid, bvid))
    # 4. save data
    replay_url = get_bili_replay_url(bvid)
    Video.objects.filter(mid=mid).update(replay_url=replay_url)
    if not Record.objects.filter(mid=mid, platform='bilibili'):
        Record.objects.create(mid=mid, platform='bilibili')
    # 5. upload video and cover to OBS
    video_object = get_obs_video_object(mid)
    metadata = generate_video_metadata(mid, video_object, video_path)
    oci = ObsClientImp(settings.ACCESS_KEY_ID, settings.SECRET_ACCESS_KEY, settings.OBS_ENDPOINT)
    upload_video_res = oci.upload_file(settings.OBS_BUCKETNAME, video_object, video_path, metadata)
    if not isinstance(upload_video_res, dict) or 'status' not in upload_video_res.keys():
        logger.error('Unexpected upload video result to OBS: {}'.format(upload_video_res))
        return
    if upload_video_res.get('status') != 200:
        logger.error('meeting {}: fail to upload video to OBS, the reason is {}'.format(mid, upload_video_res))
        return
    logger.info('meeting {}: upload video to OBS')
    upload_cover_res = oci.upload_file_without_metadata(settings.OBS_BUCKETNAME,
                                                        get_obs_cover_object(video_object),
                                                        cover_path)
    if not isinstance(upload_cover_res, dict) or 'status' not in upload_cover_res.keys():
        logger.error('Unexpected upload cover result to OBS: {}'.format(upload_video_res))
        return
    if upload_cover_res.get('status') != 200:
        logger.error('meeting {}: fail to upload cover to OBS, the reason is {}'.format(mid, upload_cover_res))
        return