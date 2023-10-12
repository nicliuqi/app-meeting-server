import datetime
import logging
import math
import requests
import secrets
import time
import yaml
from django.conf import settings
from django.middleware.csrf import get_token
from django.http import JsonResponse
from django.shortcuts import redirect
from rest_framework.filters import SearchFilter
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, CreateModelMixin, UpdateModelMixin, RetrieveModelMixin, \
    DestroyModelMixin
from multiprocessing import Process
from rest_framework.response import Response
from opengauss.send_email import sendmail
from opengauss.models import Meeting, Video, User, Group, Record
from opengauss.serializers import MeetingsSerializer, MeetingUpdateSerializer, MeetingDeleteSerializer, \
    GroupsSerializer, AllMeetingsSerializer
from opengauss.utils import cryptos
from opengauss.permissions import QueryPermission
from opengauss.utils import drivers
from opengauss.utils import send_cancel_email

logger = logging.getLogger('log')


def IdentifyUser(request):
    """
    Identify user by decrypting AES encoding
    :param request: request object
    :return: user_id
    """
    access_token = request.COOKIES.get(settings.ACCESS_TOKEN_NAME)
    if not access_token:
        return JsonResponse({'code': 400, 'msg': '请求头中缺少认证信息'})
    if not isinstance(access_token, str):
        return JsonResponse({'code': 400, 'msg': 'Bad Request'})
    if len(access_token) != 48:
        return JsonResponse({'code': 400, 'msg': 'Bad Request'})
    text, iv = access_token[:32], access_token[32:]
    user_id = int(cryptos.decrypt(text, iv.encode('utf-8')))
    return user_id


def refresh_token(user_id):
    iv = secrets.token_hex(8)
    text = cryptos.encrypt(str(user_id), iv.encode('utf-8'))
    access_token = text + iv
    return access_token


def refresh_cookie(user_id, response, access_token):
    response.delete_cookie(settings.ACCESS_TOKEN_NAME)
    now_time = datetime.datetime.now()
    expire = now_time + settings.COOKIE_EXPIRE
    expire_timestamp = int(time.mktime(expire.timetuple()))
    User.objects.filter(id=user_id).update(expire_time=expire_timestamp)
    response.set_cookie(settings.ACCESS_TOKEN_NAME, access_token, expires=expire, secure=True, httponly=True, samesite='strict')
    return response


def check_expire(expire_time, now_time):
    if not isinstance(expire_time, int) or not isinstance(now_time, int):
        return False
    if expire_time == 0:
        return False
    if now_time > expire_time:
        return False
    else:
        return True


class GiteeAuthView(GenericAPIView, ListModelMixin):
    """
    Gitee Auth
    """

    def get(self, request):
        client_id = settings.GITEE_OAUTH_CLIENT_ID
        redirect_url = settings.GITEE_OAUTH_REDIRECT
        response = {
            "client_id": client_id,
            "redirect_url": redirect_url
        }
        return JsonResponse(response)


class GiteeBackView(GenericAPIView, ListModelMixin):
    """
    Request user info through auth code and save info
    """

    def get(self, request):
        code = request.GET.get('code', None)
        client_id = settings.GITEE_OAUTH_CLIENT_ID
        client_secret = settings.GITEE_OAUTH_CLIENT_SECRET
        redirect_uri = settings.GITEE_OAUTH_REDIRECT
        url = settings.GITEE_OAUTH_URL
        params = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'client_secret': client_secret
        }
        r = requests.post(url, params=params)
        if r.status_code == 200:
            access_token = r.json()['access_token']
            r = requests.get('{}/user?access_token={}'.format(settings.GITEE_V5_API_PREFIX, access_token))
            if r.status_code == 200:
                gid = r.json()['id']
                gitee_id = r.json()['login']
                name = r.json()['name']
                avatar = r.json()['avatar_url']
                if not User.objects.filter(gid=gid):
                    User.objects.create(gid=gid, gitee_id=gitee_id, name=name, avatar=avatar)
                else:
                    User.objects.filter(gid=gid).update(gitee_id=gitee_id, name=name, avatar=avatar)
                response = redirect(settings.REDIRECT_HOME_PAGE)
                user_id = User.objects.get(gid=gid).id
                iv = secrets.token_hex(8)
                access_token = cryptos.encrypt(str(user_id), iv.encode('utf-8'))
                now_time = datetime.datetime.now()
                expire = now_time + settings.COOKIE_EXPIRE
                expire_timestamp = int(time.mktime(expire.timetuple()))
                User.objects.filter(gid=gid).update(expire_time=expire_timestamp)
                response.set_cookie(settings.ACCESS_TOKEN_NAME, access_token + iv, expires=expire, secure=True, httponly=True, samesite='strict')
                request.META['CSRF_COOKIE'] = get_token(self.request)
                return response
        else:
            return JsonResponse(r.json())


class LogoutView(GenericAPIView):
    """
    Log out
    """
    def get(self, request):
        try:
            now_time = int(time.time())
            user_id = IdentifyUser(request)
            expire_time = User.objects.get(id=user_id).expire_time
            if not check_expire(expire_time, now_time):
                return JsonResponse({'code': 401, 'msg': '身份认证过期', 'en_msg': 'Unauthorised'})
        except:
            return JsonResponse({'code': 401, 'msg': '用户未认证', 'en_msg': 'Unauthorised'})
        User.objects.filter(id=user_id).update(expire_time=0)
        response = JsonResponse({'code': 200, 'msg': 'OK'})
        response.delete_cookie(settings.ACCESS_TOKEN_NAME)
        response.delete_cookie(settings.CSRF_COOKIE_NAME)
        return response


class UserInfoView(GenericAPIView):
    """
    Get login user info
    """

    def get(self, request, *args, **kwargs):
        try:
            user_id = IdentifyUser(request)
            if not User.objects.filter(id=user_id):
                return JsonResponse({'code': 400, 'msg': 'The user does not exist'})
            user = User.objects.get(id=user_id)
            gitee_id = user.gitee_id
            with open('share/openGauss_sigs.yaml', 'r') as f:
                sigs = yaml.safe_load(f)
            self_sigs = []
            for sig in sigs:
                if gitee_id in sig['sponsors']:
                    self_sigs.append(sig['name'])
            data = {
                'user': {
                    'id': user.id,
                    'gitee_id': gitee_id
                },
                'sigs': self_sigs
            }
            return JsonResponse({'code': 200, 'msg': 'userinfo', 'data': data})
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': 400, 'msg': 'access_token错误', 'en_msg': 'Invalid access_token'})


class CreateMeetingView(GenericAPIView, CreateModelMixin):
    """
    Create a meeting
    """
    serializer_class = MeetingsSerializer
    queryset = Meeting.objects.all()

    def validate(self, request, user_id):
        now_time = datetime.datetime.now()
        err_msgs = []
        data = self.request.data
        platform = data.get('platform', 'zoom')
        host_dict = None
        date = data.get('date')
        start = data.get('start')
        end = data.get('end')
        topic = data.get('topic')
        sponsor = data.get('sponsor')
        group_name = data.get('group_name')
        etherpad = data.get('etherpad')
        if not etherpad:
            etherpad = '{}/p/{}-meetings'.format(settings.ETHERPAD_PREFIX, group_name)
        community = data.get('community', 'opengauss')
        emaillist = data.get('emaillist')
        summary = data.get('agenda')
        record = data.get('record')
        if not isinstance(platform, str):
            err_msgs.append('Field platform must be string type')
        else:
            host_dict = settings.MEETING_HOSTS.get(platform.lower())
            if not host_dict:
                err_msgs.append('Could not match any meeting host')
        try:
            start_time = datetime.datetime.strptime(' '.join([date, start]), '%Y-%m-%d %H:%M')
            end_time = datetime.datetime.strptime(' '.join([date, end]), '%Y-%m-%d %H:%M')
            if start_time <= now_time:
                err_msgs.append('The start time should not be later than the current time')
            if start_time <= end_time:
                err_msgs.append('The start time should not be later than the end time')
        except ValueError:
            err_msgs.append('Invalid start time or end time')
        if date > (datetime.datetime.today() + datetime.timedelta(days=14)).strftime('%Y-%m-%d'):
            err_msgs.append('The scheduled time cannot exceed 14')
        if sponsor != User.objects.get(id=user_id).gitee_id:
            err_msgs.append('Invalid sponsor: {}'.format(sponsor))
        if group_name not in list(Group.objects.all().values_list('name', flat=True)):
            err_msgs.append('Invalid group name: {}'.format(group_name))
        if User.objects.get(id=user_id).gitee_id not in Group.objects.get(name=group_name).members:
            err_msgs.append('Sponsor {} is not a member of group {}'.format(sponsor, group_name))
        if not etherpad.startswith(settings.ETHERPAD_PREFIX):
            err_msgs.append('Invalid etherpad address')
        if community != settings.COMMUNITY.lower():
            err_msgs.append('The field community must be the same as configure')
        if len(emaillist) > 100:
            emaillist = emaillist[:100]
        if err_msgs:
            logger.error('[CreateMeetingView] Fail to validate when creating meetings, the error messages are {}'.
                         format(','.join(err_msgs)))
            return False, None
        res = {
            'platform': platform,
            'host_dict': host_dict,
            'date': date,
            'start': start,
            'end': end,
            'topic': topic,
            'sponsor': sponsor,
            'group_name': group_name,
            'etherpad': etherpad,
            'communinty': community,
            'emaillist': emaillist,
            'summary': summary,
            'record': record
        }
        return True, res

    def post(self, request, *args, **kwargs):
        if request.COOKIES.get(settings.CSRF_COOKIE_NAME) != request.META.get('HTTP_X_CSRFTOKEN'):
            return JsonResponse({'code': 403, 'msg': 'Forbidden'})
        try:
            now_time = int(time.time())
            user_id = IdentifyUser(request)
            expire_time = User.objects.get(id=user_id).expire_time
            if not check_expire(expire_time, now_time):
                return JsonResponse({'code': 401, 'msg': '身份认证过期', 'en_msg': 'Unauthorised'})
        except:
            return JsonResponse({'code': 401, 'msg': '用户未认证', 'en_msg': 'Unauthorised'})
        is_validated, data = self.validate(request, user_id)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request', 'en_msg': 'Bad Request'})
        platform = data.get('platform', 'zoom')
        platform = platform.lower()
        host_dict = settings.MEETING_HOSTS.get('platform')
        date = data.get('date')
        start = data.get('start')
        end = data.get('end')
        topic = data.get('topic')
        sponsor = data.get('sponsor')
        group_name = data.get('group_name')
        etherpad = data.get('etherpad')
        community = data.get('community')
        emaillist = data.get('emaillist')
        summary = data.get('agenda')
        record = data.get('record')
        group_id = Group.objects.get(name=group_name).id
        start_search = datetime.datetime.strftime(
            (datetime.datetime.strptime(start, '%H:%M') - datetime.timedelta(minutes=30)),
            '%H:%M')
        end_search = datetime.datetime.strftime(
            (datetime.datetime.strptime(end, '%H:%M') + datetime.timedelta(minutes=30)),
            '%H:%M')
        # 查询待创建的会议与现有的预定会议是否冲突
        unavailable_host_id = []
        available_host_id = []
        meetings = Meeting.objects.filter(is_delete=0, date=date, end__gt=start_search, start__lt=end_search).values()
        try:
            for meeting in meetings:
                host_id = meeting['host_id']
                unavailable_host_id.append(host_id)
            logger.info('unavilable_host_id:{}'.format(unavailable_host_id))
        except KeyError:
            pass
        host_list = list(host_dict.keys())
        logger.info('host_list:{}'.format(host_list))
        for host_id in host_list:
            if host_id not in unavailable_host_id:
                available_host_id.append(host_id)
        logger.info('avilable_host_id:{}'.format(available_host_id))
        if len(available_host_id) == 0:
            logger.warning('暂无可用host')
            return JsonResponse({'code': 1000, 'msg': '时间冲突，请调整时间预定会议', 'en_msg': 'Schedule time conflict'})
        # 从available_host_id中随机生成一个host_id,并在host_dict中取出
        host_id = secrets.choice(available_host_id)
        host = host_dict[host_id]
        logger.info('host_id:{}'.format(host_id))
        logger.info('host:{}'.format(host))

        status, content = drivers.createMeeting(platform, date, start, end, topic, host, record)
        if status not in [200, 201]:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        mid = content['mid']
        start_url = content['start_url']
        join_url = content['join_url']
        host_id = content['host_id']
        timezone = content['timezone'] if 'timezone' in content else 'Asia/Shanghai'

        # 数据库生成数据
        Meeting.objects.create(
            mid=mid,
            topic=topic,
            community=community,
            sponsor=sponsor,
            group_name=group_name,
            date=date,
            start=start,
            end=end,
            etherpad=etherpad,
            emaillist=emaillist,
            timezone=timezone,
            agenda=summary,
            host_id=host_id,
            join_url=join_url,
            start_url=start_url,
            user_id=user_id,
            group_id=group_id,
            mplatform=platform
        )
        logger.info('{} has created a meeting which mid is {}.'.format(data['sponsor'], mid))
        logger.info('meeting info: {},{}-{},{}'.format(date, start, end, topic))
        # 如果开启录制功能，则在Video表中创建一条数据
        if record == 'cloud':
            Video.objects.create(
                mid=mid,
                topic=topic,
                community=community,
                group_name=group_name,
                agenda=summary
            )
            logger.info('meeting {} was created with auto recording.'.format(mid))
        # 发送email
        sequence = Meeting.objects.get(mid=mid).sequence
        m = {
            'mid': mid,
            'topic': topic,
            'date': date,
            'start': start,
            'end': end,
            'join_url': join_url,
            'sig_name': group_name,
            'toaddrs': emaillist,
            'platform': platform,
            'etherpad': etherpad,
            'summary': summary,
            'sequence': sequence
        }
        p1 = Process(target=sendmail, args=(m, record))
        p1.start()
        Meeting.objects.filter(mid=mid).update(sequence=sequence + 1)

        # 返回请求数据
        access_token = refresh_token(user_id)
        resp = {'code': 201, 'msg': '创建成功', 'en_msg': 'Schedule meeting successfully'}
        meeting_id = Meeting.objects.get(mid=mid).id
        resp['id'] = meeting_id
        response = JsonResponse(resp)
        refresh_cookie(user_id, response, access_token)
        request.META['CSRF_COOKIE'] = get_token(request)
        return response


class UpdateMeetingView(GenericAPIView, UpdateModelMixin, DestroyModelMixin, RetrieveModelMixin):
    """
    Update a meeting
    """
    serializer_class = MeetingUpdateSerializer
    queryset = Meeting.objects.filter(is_delete=0)

    def validate(self, request, user_id, mid):
        now_time = datetime.datetime.now()
        err_msgs = []
        data = self.request.data
        topic = data.get('topic')
        sponsor = data.get('sponsor')
        date = data.get('date')
        start = data.get('start')
        end = data.get('end')
        group_name = data.get('group_name')
        community = data.get('community', 'opengauss')
        summary = data.get('agenda')
        emaillist = data.get('emaillist')
        record = data.get('record')
        etherpad = data.get('etherpad')
        if not etherpad:
            etherpad = '{}/p/{}-meetings'.format(settings.ETHERPAD_PREFIX, group_name)
        if not Meeting.objects.filter(user_id=user_id, mid=mid, is_delete=0):
            err_msgs.append('Meeting {} is not exist'.format(mid))
        else:
            if Meeting.objects.get(mid=mid).user_id != user_id:
                err_msgs.append('Invalid operation: could not update a meeting others create')
        try:
            start_time = datetime.datetime.strptime(' '.join([date, start]), '%Y-%m-%d %H:%M')
            end_time = datetime.datetime.strptime(' '.join([date, end]), '%Y-%m-%d %H:%M')
            if start_time <= now_time:
                err_msgs.append('The start time should not be later than the current time')
            if start_time <= end_time:
                err_msgs.append('The start time should not be later than the end time')
        except ValueError:
            err_msgs.append('Invalid start time or end time')
        if date > (datetime.datetime.today() + datetime.timedelta(days=14)).strftime('%Y-%m-%d'):
            err_msgs.append('The scheduled time cannot exceed 14')
        if sponsor != User.objects.get(id=user_id).gitee_id:
            err_msgs.append('Invalid sponsor: {}'.format(sponsor))
        if group_name not in list(Group.objects.all().values_list('name', flat=True)):
            err_msgs.append('Invalid group name: {}'.format(group_name))
        if User.objects.get(id=user_id).gitee_id not in Group.objects.get(name=group_name).members:
            err_msgs.append('Sponsor {} is not a member of group {}'.format(sponsor, group_name))
        if not etherpad.startswith(settings.ETHERPAD_PREFIX):
            err_msgs.append('Invalid etherpad address')
        if community != settings.COMMUNITY.lower():
            err_msgs.append('The field community must be the same as configure')
        if len(emaillist) > 100:
            emaillist = emaillist[:100]
        if err_msgs:
            logger.error('[UpdateMeetingsView] Fail to validate when creating meetings, the error messages are {}'.
                         format(','.join(err_msgs)))
            return False, None
        res = {
            'date': date,
            'start': start,
            'end': end,
            'topic': topic,
            'sponsor': sponsor,
            'group_name': group_name,
            'etherpad': etherpad,
            'communinty': community,
            'emaillist': emaillist,
            'summary': summary,
            'record': record
        }
        return True, res

    def put(self, request, *args, **kwargs):
        if request.COOKIES.get(settings.CSRF_COOKIE_NAME) != request.META.get('HTTP_X_CSRFTOKEN'):
            return JsonResponse({'code': 403, 'msg': 'Forbidden'})
        # 鉴权
        try:
            now_time = int(time.time())
            user_id = IdentifyUser(request)
            expire_time = User.objects.get(id=user_id).expire_time
            if not check_expire(expire_time, now_time):
                return JsonResponse({'code': 401, 'msg': '身份认证过期', 'en_msg': 'Unauthorised'})
        except:
            return JsonResponse({'code': 401, 'msg': '用户未认证', 'en_msg': 'Unauthorised'})
        mid = self.kwargs.get('mid')
        if not Meeting.objects.filter(user_id=user_id, mid=mid, is_delete=0):
            return JsonResponse({'code': 404, 'msg': '会议不存在', 'en_msg': 'The meeting does not exist'})

        is_validated, data = self.validate(request, user_id, mid)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request', 'en_msg': 'Bad Request'})
        # 获取data
        data = self.request.data
        topic = data.get('topic')
        sponsor = data.get('sponsor')
        date = data.get('date')
        start = data.get('start')
        end = data.get('end')
        group_name = data.get('group_name')
        community = data.get('community')
        summary = data.get('agenda')
        emaillist = data.get('emaillist')
        record = data.get('record')
        etherpad = data.get('etherpad')
        group_id = Group.objects.get(name=group_name).id

        start_search = datetime.datetime.strftime(
            (datetime.datetime.strptime(start, '%H:%M') - datetime.timedelta(minutes=30)),
            '%H:%M')
        end_search = datetime.datetime.strftime(
            (datetime.datetime.strptime(end, '%H:%M') + datetime.timedelta(minutes=30)),
            '%H:%M')
        # 查询待创建的会议与现有的预定会议是否冲突
        meeting = Meeting.objects.get(mid=mid)
        host_id = meeting.host_id
        if Meeting.objects.filter(date=date, is_delete=0, host_id=host_id, end__gt=start_search, start__lt=end_search).exclude(mid=mid):
            logger.info('会议冲突！主持人在{}-{}已经创建了会议'.format(start_search, end_search))
            return JsonResponse({'code': 400, 'msg': '会议冲突！主持人在{}-{}已经创建了会议'.format(start_search, end_search),
                                 'en_msg': 'Schedule time conflict'})

        update_topic = '[Update] ' + topic
        status = drivers.updateMeeting(mid, date, start, end, update_topic, record)
        if status not in [200, 204]:
            return JsonResponse({'code': 400, 'msg': '修改会议失败', 'en_msg': 'Fail to update.'})

        # 数据库更新数据
        Meeting.objects.filter(mid=mid).update(
            topic=topic,
            sponsor=sponsor,
            group_name=group_name,
            date=date,
            start=start,
            end=end,
            etherpad=etherpad,
            emaillist=emaillist,
            agenda=summary,
            user_id=user_id,
            group_id=group_id
        )
        logger.info('{} has updated a meeting which mid is {}.'.format(sponsor, mid))
        logger.info('meeting info: {},{}-{},{}'.format(date, start, end, topic))
        # 如果开启录制功能，则在Video表中创建一条数据
        if not Video.objects.filter(mid=mid) and record == 'cloud':
            Video.objects.create(
                mid=mid,
                topic=topic,
                community=community,
                group_name=group_name,
                agenda=summary
            )
            logger.info('meeting {} was created with auto recording.'.format(mid))
        if Video.objects.filter(mid=mid) and record != 'cloud':
            Video.objects.filter(mid=mid).delete()
            logger.info('remove video obj of meeting {}'.format(mid))
        join_url = Meeting.objects.get(mid=mid).join_url
        platform = Meeting.objects.get(mid=mid).mplatform
        sequence = Meeting.objects.get(mid=mid).sequence
        m = {
            'mid': mid,
            'topic': update_topic,
            'date': date,
            'start': start,
            'end': end,
            'join_url': join_url,
            'sig_name': group_name,
            'toaddrs': emaillist,
            'platform': platform,
            'etherpad': etherpad,
            'summary': summary,
            'sequence': sequence
        }
        p1 = Process(target=sendmail, args=(m, record))
        p1.start()
        Meeting.objects.filter(mid=mid).update(sequence=sequence + 1)
        # 返回请求数据
        access_token = refresh_token(user_id)
        resp = {'code': 204, 'msg': '修改成功', 'en_msg': 'Update successfully', 'id': mid}
        response = JsonResponse(resp)
        refresh_cookie(user_id, response, access_token)
        request.META['CSRF_COOKIE'] = get_token(request)
        return response


class DeleteMeetingView(GenericAPIView, UpdateModelMixin):
    """
    Cancel a meeting
    """
    serializer_class = MeetingDeleteSerializer
    queryset = Meeting.objects.filter(is_delete=0)

    def delete(self, request, *args, **kwargs):
        if request.COOKIES.get(settings.CSRF_COOKIE_NAME) != request.META.get('HTTP_X_CSRFTOKEN'):
            return JsonResponse({'code': 403, 'msg': 'Forbidden'})
        # 鉴权
        try:
            now_time = int(time.time())
            user_id = IdentifyUser(request)
            expire_time = User.objects.get(id=user_id).expire_time
            if not check_expire(expire_time, now_time):
                return JsonResponse({'code': 401, 'msg': '身份认证过期', 'en_msg': 'Unauthorised'})
        except:
            return JsonResponse({'code': 401, 'msg': '用户未认证', 'en_msg': 'Unauthorised'})
        mid = self.kwargs.get('mid')
        if not Meeting.objects.filter(user_id=user_id, mid=mid, is_delete=0):
            return JsonResponse({'code': 404, 'msg': '会议不存在', 'en_msg': 'The meeting does not exist'})
        if Meeting.objects.get(mid=mid).user_id != user_id:
            return JsonResponse({'code': 401, 'msg': 'Forbidden', 'en_msg': 'Forbidden'})
        drivers.cancelMeeting(mid)
        # 数据库软删除数据
        Meeting.objects.filter(mid=mid).update(is_delete=1)
        user = User.objects.get(id=user_id)
        logger.info('{} has canceled meeting {}'.format(user.gitee_id, mid))
        meeting = Meeting.objects.get(mid=mid)
        date = meeting.date
        start = meeting.start
        end = meeting.end
        toaddrs = meeting.emaillist
        topic = '[Cancel] ' + meeting.topic
        sig_name = meeting.group_name
        platform = meeting.mplatform
        platform = platform.replace('zoom', 'Zoom').replace('welink', 'WeLink')
        sequence = meeting.sequence
        m = {
            'mid': mid,
            'date': date,
            'start': start,
            'end': end,
            'toaddrs': toaddrs,
            'topic': topic,
            'sig_name': sig_name,
            'platform': platform,
            'sequence': sequence
        }
        send_cancel_email.sendmail(m)
        Meeting.objects.filter(mid=mid).update(sequence=sequence + 1)
        access_token = refresh_token(user_id)
        response = JsonResponse({'code': 204, 'msg': '已删除会议{}'.format(mid), 'en_msg': 'Delete successfully'})
        refresh_cookie(user_id, response, access_token)
        request.META['CSRF_COOKIE'] = get_token(request)
        return response


class GroupsView(GenericAPIView, ListModelMixin):
    """
    Groups info
    """
    serializer_class = GroupsSerializer
    queryset = Group.objects.all()

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class MeetingsDataView(GenericAPIView, ListModelMixin):
    """
    Calendar data
    """
    queryset = Meeting.objects.filter(is_delete=0).order_by('start')
    filter_backends = [SearchFilter]
    search_fields = ['group_name']

    def get(self, request, *args, **kwargs):
        self.queryset = self.queryset.filter(
            date__gte=(datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'),
            date__lte=(datetime.datetime.now() + datetime.timedelta(days=14)).strftime('%Y-%m-%d'))
        sig_name = self.request.GET.get('group')
        if Group.objects.filter(name=sig_name):
            self.queryset = self.queryset.filter(group_name=sig_name)
        queryset = self.filter_queryset(self.get_queryset()).values()
        tableData = []
        date_list = []
        for query in queryset:
            date_list.append(query.get('date'))
        date_list = sorted(list(set(date_list)))
        if Group.objects.filter(name=sig_name):
            for date in date_list:
                tableData.append(
                    {
                        'date': date,
                        'timeData': [{
                            'id': meeting.id,
                            'mid': meeting.mid,
                            'group_name': meeting.group_name,
                            'startTime': meeting.start,
                            'endTime': meeting.end,
                            'duration': math.ceil(float(meeting.end.replace(':', '.'))) - math.floor(
                                float(meeting.start.replace(':', '.'))),
                            'duration_time': meeting.start.split(':')[0] + ':00' + '-' + str(
                                math.ceil(float(meeting.end.replace(':', '.')))) + ':00',
                            'name': meeting.topic,
                            'creator': meeting.sponsor,
                            'detail': meeting.agenda,
                            'url': User.objects.get(id=meeting.user_id).avatar,
                            'join_url': meeting.join_url,
                            'meeting_id': meeting.mid,
                            'etherpad': meeting.etherpad,
                            'record': True if Record.objects.filter(mid=meeting.mid) else False,
                            'platform': meeting.mplatform,
                            'video_url': '' if not Record.objects.filter(mid=meeting.mid, platform='bilibili') else
                            Record.objects.filter(mid=meeting.mid, platform='bilibili').values()[0]['url']
                        } for meeting in Meeting.objects.filter(is_delete=0, date=date, group_name=sig_name)]
                    }
                )
            return Response({'tableData': tableData})
        for date in date_list:
            tableData.append(
                {
                    'date': date,
                    'timeData': [{
                        'id': meeting.id,
                        'mid': meeting.mid,
                        'group_name': meeting.group_name,
                        'startTime': meeting.start,
                        'endTime': meeting.end,
                        'duration': math.ceil(float(meeting.end.replace(':', '.'))) - math.floor(
                            float(meeting.start.replace(':', '.'))),
                        'duration_time': meeting.start.split(':')[0] + ':00' + '-' + str(
                            math.ceil(float(meeting.end.replace(':', '.')))) + ':00',
                        'name': meeting.topic,
                        'creator': meeting.sponsor,
                        'detail': meeting.agenda,
                        'url': User.objects.get(id=meeting.user_id).avatar,
                        'join_url': meeting.join_url,
                        'meeting_id': meeting.mid,
                        'etherpad': meeting.etherpad,
                        'record': True if Record.objects.filter(mid=meeting.mid) else False,
                        'platform': meeting.mplatform,
                        'video_url': '' if not Record.objects.filter(mid=meeting.mid, platform='bilibili') else
                        Record.objects.filter(mid=meeting.mid, platform='bilibili').values()[0]['url']
                    } for meeting in Meeting.objects.filter(is_delete=0, date=date)]
                })
        return Response({'tableData': tableData})


class AllMeetingsView(GenericAPIView, ListModelMixin):
    """
    List all meetings
    """
    serializer_class = AllMeetingsSerializer
    queryset = Meeting.objects.all()
    filter_backends = [SearchFilter]
    search_fields = ['group_name', 'sponsor', 'date']
    permission_classes = (QueryPermission,)

    def get(self, request, *args, **kwargs):
        is_delete = self.request.GET.get('delete')
        if is_delete and is_delete in ['0', '1']:
            self.queryset = self.queryset.filter(is_delete=int(is_delete))
        return self.list(request, *args, **kwargs)


class ParticipantsView(GenericAPIView, RetrieveModelMixin):
    """
    List all participants info of a meeting
    """
    permission_classes = (QueryPermission,)

    def get(self, request, *args, **kwargs):
        mid = kwargs.get('mid')
        status, res = drivers.getParticipants(mid)
        if status == 200:
            return JsonResponse(res)
        else:
            resp = JsonResponse(res)
            resp.status_code = 400
            return resp
