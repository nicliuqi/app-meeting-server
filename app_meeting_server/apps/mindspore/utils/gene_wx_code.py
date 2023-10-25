import logging
import sys
from django.conf import settings
from obs import ObsClient
from app_meeting_server.utils import wx_apis
from app_meeting_server.utils.common import save_temp_img

logger = logging.getLogger('log')


def upload_to_obs(tmp_file, activity_id):
    access_key_id = settings.ACCESS_KEY_ID
    secret_access_key = settings.SECRET_ACCESS_KEY
    endpoint = settings.OBS_ENDPOINT
    bucket_name = settings.OBS_BUCKETNAME
    if not access_key_id or not secret_access_key or not endpoint or not bucket_name:
        logger.error('losing required arguments for ObsClient')
        sys.exit(1)
    obs_client = ObsClient(access_key_id=access_key_id,
                           secret_access_key=secret_access_key,
                           server='https://%s' % endpoint)
    object_key = 'mindspore/miniprogram/activity/{}/wx_code.jpeg'.format(activity_id)
    obs_client.uploadFile(bucketName=bucket_name, objectKey=object_key, uploadFile=tmp_file, taskNum=10,
                          enableCheckpoint=True)
    img_url = 'https://%s.%s/%s' % (bucket_name, endpoint, object_key)
    return img_url


def run(activity_id):
    content = wx_apis.gene_code_img(activity_id)
    tmp_file = save_temp_img(content)
    img_url = upload_to_obs(tmp_file, activity_id)
    return img_url
