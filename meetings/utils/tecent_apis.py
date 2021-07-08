import base64
import hashlib
import hmac
import logging
import random
import requests
import time
from django.conf import settings

logger = logging.getLogger('log')


def get_signature(method, uri, body):
    """获取签名"""
    AppId = settings.TX_MEETING_APPID
    SdkId = settings.TX_MEETING_SDKID
    secretKey = settings.TX_MEETING_SECRETKEY
    secretId = settings.TX_MEETING_SECRETID
    timestamp = str(int(time.time()))
    nonce = str(int(random.randint(0, 1000000)))
    headers = {
        "X-TC-Key": secretId,
        "X-TC-Nonce": nonce,
        "X-TC-Timestamp": timestamp,
        "X-TC-Signature": "",
        "AppId": AppId,
        "SdkId": SdkId,
        "X-TC-Registered": "1"
    }
    headerString = 'X-TC-Key=' + secretId + '&X-TC-Nonce=' + nonce + '&X-TC-Timestamp=' + timestamp
    msg = (method + '\n' + headerString + '\n' + uri + '\n' + body).encode('utf-8')
    key = secretKey.encode('utf-8')
    signature = base64.b64encode(hmac.new(key, msg, digestmod=hashlib.sha256).hexdigest().encode('utf-8')).decode(
        'utf-8')
    headers['X-TC-Signature'] = signature
    return signature, headers


def get_video_download(record_file_id, userid):
    """获取录像下载地址"""
    uri = '/v1/addresses/{}?userid={}'.format(record_file_id, userid)
    url = get_url(uri)
    signature, headers = get_signature('GET', uri, "")
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()['download_address']
    else:
        logger.error(r.text)
        return


def get_url(uri):
    """获取请求url"""
    return 'https://api.meeting.qq.com' + uri
