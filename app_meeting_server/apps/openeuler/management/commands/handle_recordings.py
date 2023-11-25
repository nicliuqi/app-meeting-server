import datetime
import logging
import os
import shutil
import traceback

import requests
from django.db.models import Q
from django.conf import settings
from django.core.management.base import BaseCommand

from app_meeting_server.utils.obs_api import ObsClientImp
from openeuler.models import Meeting, Video, Record
from multiprocessing.dummy import Pool as ThreadPool
from openeuler.utils.html_template import cover_content
from app_meeting_server.utils.welink_apis import listRecordings, downloadHWCloudRecording, getDetailDownloadUrl
from openeuler.utils.welink_apis import getParticipants
from app_meeting_server.utils.tencent_apis import get_records, get_video_download
from app_meeting_server.utils.zoom_apis import getOauthToken
from app_meeting_server.utils import zoom_apis
from app_meeting_server.utils.file_stream import write_content, download_big_file
from app_meeting_server.utils.common import execute_cmd3, gen_new_temp_dir, make_dir

logger = logging.getLogger('log')


class Command(BaseCommand):
    def handle(self, *args, **options):
        past_meetings = Meeting.objects.filter(is_delete=0).filter(
            Q(date__gt=str(datetime.datetime.now() - datetime.timedelta(days=7))) &
            Q(date__lte=datetime.datetime.now().strftime('%Y-%m-%d'))).values_list('mid', flat=True)
        meeting_ids = Video.objects.filter(mid__in=list(past_meetings)).values_list('mid', flat=True)
        record_mids = Record.objects.filter(platform='obs').values_list('mid', flat=True)
        recent_mids = list(set(meeting_ids) - set(record_mids))
        logger.info('meeting_ids: {}'.format(list(meeting_ids)))
        logger.info('mids of past_meetings: {}'.format(list(past_meetings.values_list('mid', flat=True))))
        logger.info('recent_mids: {}'.format(recent_mids))
        pool = ThreadPool()
        pool.map(run, recent_mids)
        pool.close()
        pool.join()
        logger.info('All done')


def get_obs_config():
    ak = settings.ACCESS_KEY_ID
    sk = settings.SECRET_ACCESS_KEY
    endpoint = settings.OBS_ENDPOINT
    url = 'https://%s' % endpoint
    bucket_name = settings.OBS_BUCKETNAME
    return ak, sk, endpoint, url, bucket_name


def get_zoom_recordings(mid):
    """
    查询一个host下昨日至今日(默认)的所有录像
    :param mid: 会议ID
    :return: the json-encoded content of a response or none
    """
    host_id = Meeting.objects.get(mid=mid).host_id
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


def get_participants(mid):
    """
    查询一个会议的所有参会者
    :param mid: 会议ID
    :return: the json-encoded content of a response or none
    """
    uri = '/v2/past_meetings/{}/participants?page_size=300'.format(mid)
    token = getOauthToken()
    headers = {
        'authorization': 'Bearer {}'.format(token)
    }
    response = requests.get(zoom_apis.get_url(uri), headers=headers)
    if response.status_code != 200:
        logger.error('mid: {}, get participants {} {}:'.format(mid, response.status_code, response.json()['message']))
        return
    return response.json()['participants']


def download_recordings(zoom_download_url, mid, is_zoom=True):
    """
    下载录像视频
    :param zoom_download_url: zoom提供的下载地址
    :param mid: 会议ID
    :param is_zoom: is_zoom
    :return: 下载的文件名
    """
    target_name = mid + '.mp4'
    dir_name = gen_new_temp_dir()
    make_dir(dir_name)
    filename = os.path.join(dir_name, target_name)
    r = requests.get(url=zoom_download_url, allow_redirects=False)
    if is_zoom:
        url = r.headers['location']
    else:
        url = zoom_download_url
    download_big_file(url, filename)
    return filename


def generate_cover(mid, topic, group_name, date, filename, start_time, end_time):
    """生成封面"""
    html_path = filename.replace('.mp4', '.html')
    image_path = filename.replace('.mp4', '.png')
    content = cover_content(topic, group_name, date, start_time, end_time)
    write_content(html_path, content, 'w')
    execute_cmd3("cp {} {}".format(settings.COVER_PATH, os.path.dirname(filename)))
    execute_cmd3("wkhtmltoimage --enable-local-file-access {} {}".format(html_path, image_path))
    logger.info("meeting {}: 生成封面".format(mid))
    os.remove(os.path.join(os.path.dirname(filename), 'cover.png'))


def upload_cover(filename, obs_client, bucket_name, cover_path):
    """OBS上传封面"""
    res = obs_client.uploadFile(bucketName=bucket_name, objectKey=cover_path,
                                uploadFile=filename.replace('.mp4', '.png'),
                                taskNum=10, enableCheckpoint=True)
    return res


def download_upload_recordings(start, end, zoom_download_url, mid, total_size, video, endpoint, object_key,
                               group_name, is_zoom=True):
    """
    下载、上传录像及后续操作
    :param start: 录像开始时间
    :param end: 录像结束时间
    :param zoom_download_url: zoom录像下载地址
    :param mid: 会议ID
    :param total_size: 文件大小
    :param video: Video的实例
    :param endpoint: OBS终端节点
    :param object_key: 文件在OBS上的位置
    :param group_name: sig组名
    :param is_zoom: is_zoom
    :return:
    """
    # 下载录像
    filename = download_recordings(zoom_download_url, str(mid), is_zoom=is_zoom)
    logger.info('meeting {}: 从OBS下载视频，本地保存为{}'.format(mid, filename))
    try:
        # 若下载录像的大小和total_size相等，则继续
        download_file_size = os.path.getsize(filename)
        logger.info('meeting {}: 下载的文件大小为{}'.format(mid, download_file_size))
        if download_file_size != total_size:
            logger.info("The size of the downloaded file is inconsistent with the original file")
            return
        topic = video.topic
        agenda = video.agenda
        community = video.community
        bucket_name = settings.OBS_BUCKETNAME
        if not bucket_name:
            logger.error('mid: {}, bucketName required'.format(mid))
            return
        download_url = 'https://{}.{}/{}?response-content-disposition=attachment'.format(bucket_name, endpoint,
                                                                                         object_key)
        attenders = get_participants(mid)
        # 生成metadata
        metadata = {
            "meeting_id": mid,
            "meeting_topic": topic,
            "community": community,
            "sig": group_name,
            "agenda": agenda,
            "record_start": start,
            "record_end": end,
            "download_url": download_url,
            "total_size": download_file_size,
            "attenders": []
        }
        ak, sk, _, url, bucket_name = get_obs_config()
        with ObsClientImp(ak, sk, url) as obs_client_imp:
            res = obs_client_imp.upload_file(bucket_name, object_key, filename, metadata)
            if res['status'] != 200:
                logger.info('meeting {}: OBS视频上传失败'.format(mid, filename))
                return
            logger.info('meeting {}: OBS视频上传成功'.format(mid, filename))
            # 生成封面
            date = (datetime.datetime.strptime(start.replace('T', ' ').replace('Z', ''),
                                               "%Y-%m-%d %H:%M:%S") + datetime.timedelta(hours=8)).strftime('%Y-%m-%d')
            start_time = (datetime.datetime.strptime(start.replace('T', ' ').replace('Z', ''),
                                                     "%Y-%m-%d %H:%M:%S") + datetime.timedelta(hours=8)).strftime(
                '%H:%M')
            end_time = (datetime.datetime.strptime(end.replace('T', ' ').replace('Z', ''),
                                                   "%Y-%m-%d %H:%M:%S") + datetime.timedelta(hours=8)).strftime('%H:%M')
            generate_cover(mid, topic, group_name, date, filename, start_time, end_time)
            # 上传封面
            cover_path = res['body']['key'].replace('.mp4', '.png')
            new_file_name = filename.replace('.mp4', '.png')
            res = obs_client_imp.upload_file_without_metadata(bucket_name, cover_path, new_file_name)
            if res['status'] != 200:
                logger.info('meeting {}: OBS封面上传失败'.format(mid))
                return
            logger.info('meeting {}: OBS封面上传成功'.format(mid))
            Video.objects.filter(mid=mid).update(start=start,
                                                 end=end,
                                                 total_size=total_size,
                                                 attenders=attenders,
                                                 download_url=download_url)
            url = download_url.split('?')[0]
            if Record.objects.filter(mid=mid, platform='obs').count() != 0:
                Record.objects.filter(mid=mid, platform='obs').update(
                    url=url, thumbnail=url.replace('.mp4', '.png'))
            else:
                Record.objects.create(mid=mid, platform='obs', url=url,
                                      thumbnail=url.replace('.mp4', '.png'))
            logger.info('meeting {}: 更新数据库'.format(mid))
            return topic, filename
    except Exception as e:
        logger.error("[download_upload_recordings] e:{}, traceback:{}".format(str(e), traceback.format_exc()))
    finally:
        dir_name = os.path.dirname(filename)
        if dir_name and os.path.exists(dir_name):
            shutil.rmtree(dir_name)


def handle_zoom_recordings(mid):
    # query recording data
    recordings = get_zoom_recordings(mid)
    if not recordings:
        logger.info("[handle_zoom_recordings] meeting: no recordings yet")
        return
    # filter mp4
    recordings_list = list(filter(lambda x: x if x['file_extension'] == 'MP4' else None, recordings['recording_files']))
    if len(recordings_list) == 0:
        logger.info('meeting {}: 正在录制中'.format(mid))
        return
    # filter max size
    available_recording = None
    total_size = 0
    for x in recordings_list:
        if x['file_size'] >= total_size:
            total_size = x['file_size']
            available_recording = x
    logger.info('meeting {}: 录像文件的总大小为{}'.format(mid, total_size))
    # 如果文件过小，则视为无效录像
    if total_size < 1024 * 1024 * 10:
        logger.info('meeting {}: 文件过小，不予操作'.format(mid))
        return
    # 连接obs服务，实例化ObsClient
    try:
        ak, sk, endpoint, url, bucket_name = get_obs_config()
        with ObsClientImp(ak, sk, url) as obs_client_imp:
            objs = obs_client_imp.list_objects(bucket_name)
        # 预备文件上传路径
        start = available_recording['recording_start']
        month = datetime.datetime.strptime(start.replace('T', ' ').replace('Z', ''),
                                           "%Y-%m-%d %H:%M:%S").strftime("%b").lower()
        video = Video.objects.get(mid=mid)
        group_name = video.group_name
        video_name = mid + '.mp4'
        object_key = 'openeuler/{}/{}/{}/{}'.format(group_name, month, mid, video_name)
        logger.info('meeting {}: object_key is {}'.format(mid, object_key))
        # 收集录像信息待用
        end = available_recording['recording_end']
        zoom_download_url = available_recording['download_url']
        if not objs:
            logger.info('meeting {}: OBS无存储对象，开始下载视频'.format(mid))
            download_upload_recordings(start, end, zoom_download_url, mid, total_size, video,
                                       endpoint, object_key, group_name)
        else:
            key_size_map = {x['key']: x['size'] for x in objs}
            if object_key not in key_size_map.keys():
                logger.info('meeting {}: OBS存储服务中无此对象，开始下载视频'.format(mid))
                download_upload_recordings(start, end, zoom_download_url, mid, total_size, video,
                                           endpoint, object_key,
                                           group_name)
            elif object_key in key_size_map.keys() and key_size_map[object_key] >= total_size:
                logger.info('meeting {}: OBS存储服务中已存在该对象且无需替换'.format(mid))
            else:
                logger.info('meeting {}: OBS存储服务中该对象需要替换，开始下载视频'.format(mid))
                download_upload_recordings(start, end, zoom_download_url, mid, total_size, video,
                                           endpoint,
                                           object_key, group_name)
    except Exception as e:
        logger.error("[handle_zoom_recordings] e:{}, traceback:{}".format(str(e), traceback.format_exc()))


def get_welink_meeting_participants(mid):
    _, participants = getParticipants(mid)
    if 'participants' in participants.keys():
        return participants['participants']
    else:
        return participants


def get_available_recordings(mid, host_id, start_time, end_time):
    status, recordings = listRecordings(host_id)
    available_recordings = list()
    if status != 200:
        logger.info('Fail to get welink recordings')
        return available_recordings
    if recordings['count'] == 0:
        return available_recordings
    recordings_data = recordings['data']
    start_order_set = set()
    for recording in recordings_data:
        conf_id = recording['confID']
        start_time_format = (datetime.datetime.strptime(recording['startTime'], '%Y-%m-%d %H:%M') +
                             datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')
        rcd_time = recording['rcdTime']
        if conf_id != mid:
            continue
        end_time_format = (datetime.datetime.strptime(start_time_format, '%Y-%m-%d %H:%M') + datetime.timedelta(seconds=rcd_time)). \
            strftime('%Y-%m-%d %H:%M')
        if end_time_format < start_time or start_time_format > end_time:
            continue
        start_order_set.add(start_time_format)
    for st in sorted(list(start_order_set)):
        for recording in recordings_data:
            conf_id = recording['confID']
            start_time_format = (datetime.datetime.strptime(recording['startTime'], '%Y-%m-%d %H:%M') +
                                 datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')
            rcd_time = recording['rcdTime']
            if conf_id != mid:
                continue
            end_time_format = (datetime.datetime.strptime(start_time_format, '%Y-%m-%d %H:%M') + datetime.timedelta(seconds=rcd_time)). \
                strftime('%Y-%m-%d %H:%M')
            if end_time_format < start_time or start_time_format > end_time:
                continue
            if start_time_format == st:
                available_recordings.append(recording)
    return available_recordings


def download_upload_welink_recordings(start, end, mid, filename, object_key, endpoint, group_name):
    download_file_size = os.path.getsize(filename)
    video = Video.objects.get(mid=mid)
    topic = video.topic
    if '-' in filename:
        order_number = int(filename.split('-')[-1].split('.')[0])
        topic = (video.topic + '-{}'.format(order_number))
    agenda = video.agenda
    community = video.community
    bucket_name = settings.OBS_BUCKETNAME
    if not bucket_name:
        logger.error('mid: {}, bucketName required'.format(mid))
        return
    download_url = 'https://{}.{}/{}?response-content-disposition=attachment'.format(bucket_name, endpoint, object_key)
    attenders = get_welink_meeting_participants(mid)
    metadata = {
        "meeting_id": mid,
        "meeting_topic": topic,
        "community": community,
        "sig": group_name,
        "agenda": agenda,
        "record_start": start,
        "record_end": end,
        "download_url": download_url,
        "total_size": download_file_size,
        "attenders": []
    }
    try:
        ak, sk, _, url, bucket_name = get_obs_config()
        with ObsClientImp(ak, sk, url) as obs_client_imp:
            res = obs_client_imp.upload_file(bucket_name, object_key, filename, metadata)
            if res['status'] != 200:
                logger.info('meeting {}: OBS视频上传失败'.format(mid, filename))
                return
            logger.info('meeting {}: OBS视频上传成功'.format(mid, filename))
            # 生成封面
            meeting = Meeting.objects.get(mid=mid)
            date = meeting.date
            start = meeting.start
            end = meeting.end
            generate_cover(mid, topic, group_name, date, filename, start, end)
            # 上传封面
            cover_path = res['body']['key'].replace('.mp4', '.png')
            new_file_name = filename.replace('.mp4', '.png')
            res = obs_client_imp.upload_file_without_metadata(bucket_name, cover_path, new_file_name)
            if res["status"] != 200:
                logger.info('meeting {}: OBS封面上传失败'.format(mid))
                return
            logger.info('meeting {}: OBS封面上传成功'.format(mid))
        if '-' not in filename or '-1' in filename:
            Video.objects.filter(mid=mid).update(start=start,
                                                 end=end,
                                                 total_size=download_file_size,
                                                 attenders=attenders,
                                                 download_url=download_url)
        url = download_url.split('?')[0]
        if Record.objects.filter(mid=mid, platform='obs').count() != 0:
            Record.objects.filter(mid=mid, platform='obs').update(
                url=url, thumbnail=url.replace('.mp4', '.png'))
        else:
            Record.objects.create(mid=mid, platform='obs', url=url,
                                  thumbnail=url.replace('.mp4', '.png'))
        logger.info('meeting {}: 更新数据库'.format(mid))
        return topic, filename
    except Exception as e:
        logger.error('meeting {}: upload file error! {}'.format(mid, str(e)))
    finally:
        if filename and os.path.exists(filename):
            dir_name = os.path.dirname(filename)
            shutil.rmtree(dir_name)


def after_download_recording(target_filename, start, end, mid, target_name):
    if not os.path.exists(target_filename):
        logger.error("[after_download_recording] dont find file")
    total_size = os.path.getsize(target_filename)
    # 连接obs服务，实例化ObsClient
    ak, sk, endpoint, url, bucket_name = get_obs_config()
    try:
        with ObsClientImp(ak, sk, url) as obs_client_imp:
            obs_objs = obs_client_imp.list_objects(bucket_name)
        # 预备文件上传路径
        date = Meeting.objects.get(mid=mid).date
        start_time = date + 'T' + start + ':00Z'
        end_time = date + 'T' + end + ':00Z'
        month = datetime.datetime.strptime(start_time.replace('T', ' ').replace('Z', ''),
                                           "%Y-%m-%d %H:%M:%S").strftime("%b").lower()
        video = Video.objects.get(mid=mid)
        group_name = video.group_name
        object_key = 'openeuler/{}/{}/{}/{}'.format(group_name, month, mid, target_name)
        logger.info('meeting {}: object_key is {}'.format(mid, object_key))
        # 收集录像信息待用
        if not obs_objs:
            logger.info('meeting {}: OBS无存储对象，开始下载视频'.format(mid))
            download_upload_welink_recordings(start_time, end_time, mid, target_filename,
                                              object_key, endpoint, group_name)
        else:
            key_size_map = {x['key']: x['size'] for x in obs_objs}
            if object_key not in key_size_map.keys():
                logger.info('meeting {}: OBS存储服务中无此对象，开始下载视频'.format(mid))
                download_upload_welink_recordings(start_time, end_time, mid, target_filename,
                                                  object_key, endpoint, group_name)
            elif object_key in key_size_map.keys() and key_size_map[object_key] >= total_size:
                logger.info('meeting {}: OBS存储服务中已存在该对象且无需替换'.format(mid))
            else:
                logger.info('meeting {}: OBS存储服务中该对象需要替换，开始下载视频'.format(mid))
                download_upload_welink_recordings(start_time, end_time, mid, target_filename,
                                                  object_key, endpoint, group_name)
    except Exception as e:
        logger.error("[after_download_recording] e:{}, traceback:{}".format(str(e), traceback.format_exc()))


def handle_welink_recordings(mid):
    meeting = Meeting.objects.get(mid=mid)
    date = meeting.date
    start = meeting.start
    end = meeting.end
    start_time = date + ' ' + start
    end_time = date + ' ' + end
    host_id = meeting.host_id
    available_recordings = get_available_recordings(mid, host_id, start_time, end_time)
    if not available_recordings:
        logger.info('meeting {}: 无可用录像'.format(mid))
        return
    waiting_download_recordings = []
    for available_recording in available_recordings:
        conf_uuid = available_recording['confUUID']
        status, res = getDetailDownloadUrl(conf_uuid, host_id)
        record_urls = res['recordUrls'][0]['urls']
        for record_url in record_urls:
            if record_url['fileType'].lower() in ['hd', 'aux']:
                waiting_download_recordings.append(record_url)
    dir_name = gen_new_temp_dir()
    make_dir(dir_name)
    target_name = mid + '.mp4'
    target_filename = os.path.join(dir_name, target_name)
    token = waiting_download_recordings[0]['token']
    download_url = waiting_download_recordings[0]['url']
    downloadHWCloudRecording(token, target_filename, download_url)
    after_download_recording(target_filename, start, end, mid, target_name)


def handle_tencent_recordings(mid):
    # 参数准备
    meeting = Meeting.objects.get(mid=mid)
    video = Video.objects.get(mid=mid)
    mmid = meeting.mmid
    date = meeting.date
    start = meeting.start
    start_time = ' '.join([date, start])
    start_timestamp = int(datetime.datetime.timestamp(datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M')))
    # 获取账户级会议录制列表
    records = get_records()
    if not records:
        logger.error("[handle_tencent_recordings] get empty records")
        return
    # 遍历录制列表，匹配录制文件
    match_record = {}
    for record in records:
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
    total_size = match_record['record_size']
    # 获取录像下载链接
    download_url = get_video_download(match_record.get('record_file_id'), match_record.get('userid'))
    if not download_url:
        logger.error("get empty url")
        return
    # 连接obs服务，实例化ObsClient
    ak, sk, endpoint, url, bucket_name = get_obs_config()
    with ObsClientImp(ak, sk, url) as obs_client_imp:
        objs = obs_client_imp.list_objects(bucket_name)
    # 预备文件上传路径
    start = date + 'T' + start + ':00Z'
    month = datetime.datetime.strptime(start.replace('T', ' ').replace('Z', ''),
                                       "%Y-%m-%d %H:%M:%S").strftime("%b").lower()
    group_name = video.group_name
    video_name = mid + '.mp4'
    object_key = 'openeuler/{}/{}/{}/{}'.format(group_name, month, mid, video_name)
    logger.info('meeting {}: object_key is {}'.format(mid, object_key))
    # 收集录像信息待用
    end = date + 'T' + meeting.end + ':00Z'
    if not objs:
        logger.info('meeting {}: OBS无存储对象，开始下载视频'.format(mid))
        download_upload_recordings(start, end, download_url, mid, total_size, video,
                                   endpoint, object_key,
                                   group_name, is_zoom=False)
    else:
        key_size_map = {x['key']: x['size'] for x in objs}
        if object_key not in key_size_map.keys():
            logger.info('meeting {}: OBS存储服务中无此对象，开始下载视频'.format(mid))
            download_upload_recordings(start, end, download_url, mid, total_size, video,
                                       endpoint, object_key,
                                       group_name, is_zoom=False)
        elif object_key in key_size_map.keys() and key_size_map[object_key] >= total_size:
            logger.info('meeting {}: OBS存储服务中已存在该对象且无需替换'.format(mid))
        else:
            logger.info('meeting {}: OBS存储服务中该对象需要替换，开始下载视频'.format(mid))
            download_upload_recordings(start, end, download_url, mid, total_size, video,
                                       endpoint,
                                       object_key, group_name, is_zoom=False)


def run(mid):
    """
    查询Video根据total_size判断是否需要执行后续操作（下载、上传、保存数据）
    :param mid: 会议ID
    :return:
    """
    logger.info('meeting {}: 开始处理'.format(mid))
    platform = Meeting.objects.get(mid=mid).mplatform
    if platform == 'zoom':
        try:
            handle_zoom_recordings(mid)
        except Exception as e:
            logger.error("handle_zoom_recordings {}, and traceback:{}".format(e, traceback.format_exc()))
    elif platform == 'welink':
        try:
            handle_welink_recordings(mid)
        except Exception as e:
            logger.error("handle_welink_recordings {}, and traceback:{}".format(e, traceback.format_exc()))
    elif platform == 'tencent':
        try:
            handle_tencent_recordings(mid)
        except Exception as e:
            logger.error("handle_tencent_recordings {}, and traceback:{}".format(e, traceback.format_exc()))
