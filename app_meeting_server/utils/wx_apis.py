import json
import logging
import requests
import sys
from django.conf import settings

logger = logging.getLogger('log')


def get_token():
    """获取微信小程序token"""
    appid = settings.APP_CONF['appid']
    secret = settings.APP_CONF['secret']
    uri = '/cgi-bin/token'
    params = {
        'appid': appid,
        'secret': secret,
        'grant_type': 'client_credential'
    }
    r = requests.get(get_url(uri), params=params)
    if r.status_code != 200:
        logger.error('fail to get wx access_token')
        logger.error('status_code: {}'.format(r.status_code))
        logger.error('content: {}'.format(r.json()))
        return ''
    access_token = r.json().get('access_token')
    return access_token


def get_openid(code):
    """获取小程序用户openid"""
    uri = '/sns/jscode2session'
    params = {
        'appid': settings.APP_CONF['appid'],
        'secret': settings.APP_CONF['secret'],
        'js_code': code,
        'grant_type': 'authorization_code'
    }
    r = requests.get(get_url(uri), params=params)
    return r.json()


def send_subscription(content, access_token):
    """发送订阅消息"""
    uri = '/cgi-bin/message/subscribe/send'
    params = {
        'access_token': access_token
    }
    response = requests.post(get_url(uri), params=params, data=json.dumps(content))
    return response


def gene_code_img(activity_id):
    """生成二维码"""
    access_token = get_token()
    uri = '/wxa/getwxacodeunlimit'
    params = {
        'access_token': access_token
    }
    data = {
        'scene': activity_id,
        'page': 'package-events/events/event-detail'
    }
    res = requests.post(get_url(uri), params=params, data=json.dumps(data))
    if res.status_code != 200:
        logger.error('{}, fail to get QR code'.format(res.status_code))
        sys.exit(1)
    return res.content


def get_start_template(openid, meeting_id, topic, time):
    """获取开始通知模板"""
    if len(topic) > 20:
        topic = topic[:20]
    page = '/pages/meeting/detail?id={}'.format(meeting_id)
    if settings.COMMUNITY == 'mindspore':
        page = '/package-meeting/meeting/detail?id={}'.format(meeting_id)
    content = {
        'touser': openid,
        'template_id': settings.MEETING_ATTENTION_TEMPLATE,
        'page': page,
        'lang': 'zh-CN',
        'data': {
            'thing7': {
                'value': topic
            },
            'date2': {
                'value': time
            },
            'thing6': {
                'value': '会议即将开始'
            }
        }
    }
    return content


def get_remove_template(openid, topic, time, mid):
    """获取取消通知模板"""
    if len(topic) > 20:
        topic = topic[:20]
    content = {
        'touser': openid,
        'template_id': settings.CANCEL_MEETING_TEMPLATE,
        'page': '/pages/index/index',
        'lang': 'zh-CN',
        'data': {
            'thing1': {
                'value': topic
            },
            'time2': {
                'value': time
            },
            'thing4': {
                'value': '会议{}已被取消'.format(mid)
            }
        }
    }
    return content


def get_url(uri):
    prefix = settings.WX_API_PREFIX
    return prefix + uri