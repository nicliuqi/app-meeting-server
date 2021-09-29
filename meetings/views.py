import datetime
import json
import os
import re
import sys
import tempfile
import traceback
import wget
from django.conf import settings
from multiprocessing import Process
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from rest_framework import permissions
from rest_framework.filters import SearchFilter
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin, ListModelMixin, RetrieveModelMixin, \
    DestroyModelMixin
from rest_framework_simplejwt import authentication
from meetings.models import Meeting, Record
from meetings.permissions import MaintainerPermission, AdminPermission, QueryPermission
from meetings.models import GroupUser, Group, User, Collect, Feedback
from meetings.serializers import LoginSerializer, UsersInGroupSerializer, SigsSerializer, GroupsSerializer, \
     GroupUserAddSerializer, GroupUserDelSerializer, UserInfoSerializer, UserGroupSerializer, MeetingSerializer, \
     MeetingDelSerializer, MeetingDetailSerializer, MeetingsListSerializer, CollectSerializer, FeedbackSerializer
from meetings.send_email import sendmail
from meetings.utils.tecent_apis import *
from meetings.utils import send_feedback
from obs import ObsClient

logger = logging.getLogger('log')


class LoginView(GenericAPIView, CreateModelMixin, ListModelMixin):
    """用户注册与授权登陆"""
    serializer_class = LoginSerializer
    queryset = User.objects.all()

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save()


class GroupMembersView(GenericAPIView, ListModelMixin):
    """组成员列表"""
    serializer_class = UsersInGroupSerializer
    queryset = User.objects.all()
    filter_backends = [SearchFilter]
    search_fields = ['nickname']

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        try:
            group_name = self.request.GET.get('group')
            if Group.objects.filter(name=group_name):
                group_id = Group.objects.get(name=group_name).id
                groupusers = GroupUser.objects.filter(group_id=group_id)
                ids = [x.user_id for x in groupusers]
                user = User.objects.filter(id__in=ids)
                return user
        except KeyError:
            pass


class NonGroupMembersView(GenericAPIView, ListModelMixin):
    """非组成员列表"""
    serializer_class = UsersInGroupSerializer
    queryset = User.objects.all()
    filter_backends = [SearchFilter]
    search_fields = ['nickname']

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        try:
            group_name = self.request.GET.get('group')
            if Group.objects.filter(name=group_name):
                group_id = Group.objects.get(name=group_name).id
                groupusers = GroupUser.objects.filter(group_id=group_id)
                ids = [x.user_id for x in groupusers]
                user = User.objects.filter().exclude(id__in=ids)
                return user
        except KeyError:
            pass


class SigsView(GenericAPIView, ListModelMixin):
    """SIG列表"""
    serializer_class = SigsSerializer
    queryset = Group.objects.filter(group_type=1)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class GroupsView(GenericAPIView, ListModelMixin):
    """组信息"""
    serializer_class = GroupsSerializer
    queryset = Group.objects.all()

    def get(self, request, *args, **kwargs):
        self.queryset = self.queryset.filter(group_type__in=(2, 3))
        return self.list(request, *args, **kwargs)


class GroupUserAddView(GenericAPIView, CreateModelMixin):
    """批量新增成员"""
    serializer_class = GroupUserAddSerializer
    queryset = GroupUser.objects.all()
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (AdminPermission,)

    def post(self, request, *args, **kwargs):
        print('data: {}'.format(self.request.data))
        return self.create(request, *args, **kwargs)


class GroupUserDelView(GenericAPIView, CreateModelMixin):
    """批量删除组成员"""
    serializer_class = GroupUserDelSerializer
    queryset = GroupUser.objects.all()
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (AdminPermission,)

    def post(self, request, *args, **kwargs):
        print('data: {}'.format(self.request.data))
        group_id = self.request.data.get('group_id')
        ids = self.request.data.get('ids')
        ids_list = [int(x) for x in ids.split('-')]
        GroupUser.objects.filter(group_id=group_id, user_id__in=ids_list).delete()
        return JsonResponse({'code': 204, 'msg': '删除成功'})


class UserInfoView(GenericAPIView, RetrieveModelMixin):
    """查询用户信息"""
    serializer_class = UserInfoSerializer
    queryset = User.objects.all()
    authentication_classes = (authentication.JWTAuthentication,)

    def get(self, request, *args, **kwargs):
        user_id = kwargs.get('pk')
        if user_id != request.user.id:
            logger.warning('user_id did not match.')
            logger.warning('user_id:{}, request.user.id:{}'.format(user_id, request.user.id))
            return JsonResponse({"code": 400, "message": "错误操作，信息不匹配！"})
        return self.retrieve(request, *args, **kwargs)


class UserGroupView(GenericAPIView, ListModelMixin):
    """查询用户所在SIG组信息"""
    serializer_class = UserGroupSerializer
    queryset = GroupUser.objects.all()

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        try:
            usergroup = GroupUser.objects.filter(user_id=self.kwargs['pk']).all()
            return usergroup
        except KeyError:
            pass


class UpdateUserInfoView(GenericAPIView, UpdateModelMixin):
    """修改用户信息"""
    serializer_class = UserInfoSerializer
    queryset = User.objects.all()
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (AdminPermission,)

    def put(self, request, *args, **kwargs):
        print('data: {}'.format(self.request.data))
        return self.update(request, *args, **kwargs)


class CreateMeetingView(GenericAPIView, CreateModelMixin):
    """预定会议"""
    serializer_class = MeetingSerializer
    queryset = Meeting.objects.all()
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (MaintainerPermission,)

    def post(self, *args, **kwargs):
        data = self.request.data
        host_list = settings.MINDSPORE_MEETING_HOSTS
        topic = data['topic']
        sponsor = data['sponsor']
        meeting_type = data['meeting_type']
        date = data['date']
        start = data['start']
        end = data['end']
        etherpad = data['etherpad']
        group_name = data['group_name']
        community = 'mindspore'
        emaillist = data['emaillist'] if 'emaillist' in data else None
        agenda = data['agenda'] if 'agenda' in data else None
        record = data['record'] if 'record' in data else None
        user_id = self.request.user.id
        if not Group.objects.filter(name=group_name):
            return JsonResponse({'code': 400, 'msg': '错误的group_name'})
        group_id = Group.objects.get(name=group_name).id
        # 根据时间判断当前可用host，并选择host
        start_time = date + ' ' + start
        end_time = date + ' ' + end
        if start_time < datetime.datetime.now().strftime('%Y-%m-%d %H:%M'):
            logger.warning('The start time should not be earlier than the current time.')
            return JsonResponse({'code': 1005, 'message': '请输入正确的开始时间'})
        if start >= end:
            logger.warning('The end time must be greater than the start time.')
            return JsonResponse({'code': 1001, 'message': '请输入正确的结束时间'})
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
        logger.info('host_list: {}'.format(host_list))
        for host_id in host_list:
            if host_id not in unavailable_host_id:
                available_host_id.append(host_id)
        logger.info('avilable_host_id: {}'.format(available_host_id))
        if len(available_host_id) == 0:
            logger.warning('暂无可用host')
            return JsonResponse({'code': 1000, 'message': '时间冲突，请调整时间预定会议！'})
        # 从available_host_id中随机生成一个host_id,并在host_dict中取出
        host_id = random.choice(available_host_id)
        logger.info('host_id: {}'.format(host_id))
        start_time = str(int(time.mktime(time.strptime(start_time, '%Y-%m-%d %H:%M'))))
        end_time = str(int(time.mktime(time.strptime(end_time, '%Y-%m-%d %H:%M'))))
        payload = {
            "userid": host_id,
            "instanceid": 1,
            "subject": topic,
            "type": 0,
            "start_time": start_time,
            "end_time": end_time,
            "settings": {
                "mute_enable_join": True
            }
        }
        if record == 'cloud':
            payload['settings']['auto_record_type'] = 'cloud'
            payload['settings']['participant_join_auto_record'] = True
            payload['settings']['enable_host_pause_auto_record'] = True
        uri = '/v1/meetings'
        url = get_url(uri)
        payload = json.dumps(payload)
        signature, headers = get_signature('POST', uri, payload)
        r = requests.post(url, headers=headers, data=payload)
        if r.status_code == 200:
            meeting_id = r.json()['meeting_info_list'][0]['meeting_id']
            meeting_code = r.json()['meeting_info_list'][0]['meeting_code']
            join_url = r.json()['meeting_info_list'][0]['join_url']
            # 保存数据
            Meeting.objects.create(
                mid=meeting_code,
                mmid=meeting_id,
                topic=topic,
                community=community,
                meeting_type=meeting_type,
                group_type=meeting_type,
                sponsor=sponsor,
                agenda=agenda,
                date=date,
                start=start,
                end=end,
                join_url=join_url,
                etherpad=etherpad,
                emaillist=emaillist,
                group_name=group_name,
                host_id=host_id,
                user_id=user_id,
                group_id=group_id
            )
            logger.info('{} has created a meeting which mid is {}.'.format(sponsor, meeting_code))
            logger.info('meeting info: {},{}-{},{}'.format(date, start, end, topic))
            # 发送邮件
            if group_name == 'Tech':
                group_name = '专家委员会'
            p1 = Process(target=sendmail, args=(topic, date, start, join_url, group_name, emaillist, agenda, record))
            p1.start()
            meeting_id = Meeting.objects.get(mid=meeting_code).id
            return JsonResponse({'code': 201, 'msg': '创建成功', 'id': meeting_id})
        else:
            logger.error(r.json())
            return JsonResponse({'code': 400, 'msg': '创建失败'})


class CancelMeetingView(GenericAPIView, UpdateModelMixin):
    """取消会议"""
    serializer_class = MeetingDelSerializer
    queryset = Meeting.objects.all()
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (MaintainerPermission,)

    def put(self, *args, **kwargs):
        user_id = self.request.user.id
        mmid = self.kwargs.get('mmid')
        if not Meeting.objects.filter(mmid=mmid, user_id=user_id, is_delete=0):
            return JsonResponse({'code': 400, 'msg': '会议不存在'})
        meeting = Meeting.objects.get(mmid=mmid)
        host_id = meeting.host_id
        mid = meeting.mid
        payload = json.dumps({
            "userid": host_id,
            "instanceid": 1,
            "reason_code": 1
        })
        uri = '/v1/meetings/' + str(mmid) + '/cancel'
        url = get_url(uri)
        signature, headers = get_signature('POST', uri, payload)
        r = requests.post(url, headers=headers, data=payload)
        # 数据库更改Meeting的is_delete=1
        if r.status_code == 200:
            Meeting.objects.filter(mmid=mmid).update(is_delete=1)
            # 发送会议取消通知
            collections = Collect.objects.filter(meeting_id=meeting.id)
            if collections:
                access_token = self.get_token()
                topic = meeting.topic
                date = meeting.date
                start_time = meeting.start
                time = date + ' ' + start_time
                for collection in collections:
                    user_id = collection.user_id
                    user = User.objects.get(id=user_id)
                    nickname = user.nickname
                    openid = user.openid
                    content = self.get_remove_template(openid, topic, time, mid)
                    r = requests.post(
                        'https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={}'.format(access_token),
                        data=json.dumps(content))
                    if r.status_code != 200:
                        logger.error('status code: {}'.format(r.status_code))
                        logger.error('content: {}'.format(r.json()))
                    else:
                        if r.json()['errcode'] != 0:
                            logger.warning('Error Code: {}'.format(r.json()['errcode']))
                            logger.warning('Error Msg: {}'.format(r.json()['errmsg']))
                            logger.warning('receiver: {}'.format(nickname))
                        else:
                            logger.info('meeting {} cancel message sent to {}.'.format(mid, nickname))
                    # 删除收藏
                    collection.delete()
            logger.info('{} has canceled the meeting which mid was {}'.format(self.request.user.gitee_name, mid))
            return JsonResponse({'code': 200, 'msg': '取消会议'})
        else:
            logger.error('删除会议失败')
            logger.error(r.json())
            return JsonResponse({'code': 400, 'msg': '取消失败'})

    def get_remove_template(self, openid, topic, time, mid):
        if len(topic) > 20:
            topic = topic[:20]
        content = {
            "touser": openid,
            "template_id": settings.MINDSPORE_CANCEL_MEETING_TEMPLATE,
            "page": "/pages/index/index",
            "miniprogram_state": "trial",
            "lang": "zh-CN",
            "data": {
                "thing1": {
                    "value": topic
                },
                "time2": {
                    "value": time
                },
                "thing4": {
                    "value": "会议{}已被取消".format(mid)
                }
            }
        }
        return content

    def get_token(self):
        appid = settings.MINDSPORE_APP_CONF['appid']
        secret = settings.MINDSPORE_APP_CONF['secret']
        url = 'https://api.weixin.qq.com/cgi-bin/token?appid={}&secret={}&grant_type=client_credential'.format(appid,
                                                                                                               secret)
        r = requests.get(url)
        if r.status_code == 200:
            try:
                access_token = r.json()['access_token']
                return access_token
            except KeyError as e:
                logger.error(e)
        else:
            logger.error(r.json())
            logger.error('fail to get access_token,exit.')
            sys.exit(1)


class MeetingDetailView(GenericAPIView, RetrieveModelMixin):
    """会议详情"""
    serializer_class = MeetingDetailSerializer
    queryset = Meeting.objects.filter(is_delete=0)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class MeetingsListView(GenericAPIView, ListModelMixin):
    """会议列表"""
    serializer_class = MeetingsListSerializer
    queryset = Meeting.objects.filter(is_delete=0)

    def get(self, request, *args, **kwargs):
        today = datetime.datetime.strftime(datetime.datetime.today(), '%Y-%m-%d')
        meeting_range = self.request.GET.get('range')
        meeting_type = self.request.GET.get('type')
        try:
            if meeting_type == 'sig':
                self.queryset = self.queryset.filter(meeting_type=1)
            if meeting_type == 'msg':
                self.queryset = self.queryset.filter(meeting_type=2)
            if meeting_type == 'tech':
                self.queryset = self.queryset.filter(meeting_type=3)
        except:
            pass
        if meeting_range == 'daily':
            self.queryset = self.queryset.filter(date=today).order_by('start')
        if meeting_range == 'weekly':
            week_before = datetime.datetime.strftime(datetime.datetime.today() - datetime.timedelta(days=7), '%Y-%m-%d')
            week_later = datetime.datetime.strftime(datetime.datetime.today() + datetime.timedelta(days=7), '%Y-%m-%d')
            self.queryset = self.queryset.filter(Q(date__gte=week_before) & Q(date__lte=week_later)).order_by('-date',
                                                                                                              'start')
        if meeting_range == 'recently':
            self.queryset = self.queryset.filter(date__gte=today).order_by('date', 'start')
        return self.list(request, *args, **kwargs)


class CollectMeetingView(GenericAPIView, CreateModelMixin):
    """收藏会议"""
    serializer_class = CollectSerializer
    queryset = Collect.objects.all()
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        user_id = self.request.user.id
        meeting_id = self.request.data['meeting']
        if not meeting_id:
            return JsonResponse({'code': 400, 'msg': 'meeting不能为空'})
        if not Collect.objects.filter(meeting_id=meeting_id, user_id=user_id):
            Collect.objects.create(meeting_id=meeting_id, user_id=user_id)
        return JsonResponse({'code': 201, 'msg': '收藏成功'})


class CollectionDelView(GenericAPIView, DestroyModelMixin):
    """取消收藏会议"""
    serializer_class = CollectSerializer
    queryset = Collect.objects.all()
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Collect.objects.filter(user_id=self.request.user.id)
        return queryset


class MyMeetingsView(GenericAPIView, ListModelMixin):
    """我预定的所有会议"""
    serializer_class = MeetingsListSerializer
    queryset = Meeting.objects.all().filter(is_delete=0)
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (authentication.JWTAuthentication,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        user_id = self.request.user.id
        queryset = Meeting.objects.filter(is_delete=0, user_id=user_id).order_by('-date', 'start')
        if User.objects.get(id=user_id).level == 3:
            queryset = Meeting.objects.filter(is_delete=0).order_by('-date', 'start')
        return queryset


class MyCollectionsView(GenericAPIView, ListModelMixin):
    """我收藏的会议"""
    serializer_class = MeetingsListSerializer
    queryset = Meeting.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (authentication.JWTAuthentication,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        user_id = self.request.user.id
        collection_lst = Collect.objects.filter(user_id=user_id).values_list('meeting', flat=True)
        queryset = Meeting.objects.filter(is_delete=0, id__in=collection_lst).order_by('-date', 'start')
        return queryset


class FeedbackView(GenericAPIView, CreateModelMixin):
    """意见反馈"""
    serializer_class = FeedbackSerializer
    queryset = Feedback.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (authentication.JWTAuthentication,)

    def post(self, request, *args, **kwargs):
        data = self.request.data
        try:
            feedback_type = data['feedback_type']
            feedback_content = data['feedback_content']
            feedback_email = data['feedback_email']
            if not re.match(r'^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$', feedback_email):
                return JsonResponse({'code': 400, 'msg': '请填入正确的收件邮箱'})
            user_id = self.request.user.id
            Feedback.objects.create(
                feedback_type=feedback_type,
                feedback_content=feedback_content,
                feedback_email=feedback_email,
                user_id=user_id
            )
            if feedback_type == 1:
                feedback_type = '问题反馈'
            if feedback_type == 2:
                feedback_type = '产品建议'
            send_feedback.run(feedback_type, feedback_email, feedback_content)
            return JsonResponse({'code': 201, 'msg': '反馈意见已收集'})
        except KeyError:
            return JsonResponse(
                {'code': 400, 'msg': 'feedback_type, feedback_content and feedback_email are all required!'})


class HandleRecordView(GenericAPIView):
    """处理录像"""

    def get(self, request, *args, **kwargs):
        check_str = self.request.GET.get('check_str')
        return HttpResponse(base64.b64decode(check_str.encode('utf-8')).decode('utf-8'))

    def post(self, request, *args, **kwargs):
        data = self.request.data
        bdata = data['data']
        real_data = json.loads(base64.b64decode(bdata.encode('utf-8')).decode('utf-8'))
        logger.info('completed recording payload: {}'.format(real_data))
        # 从real_data从获取会议的id, code, record_file_id
        try:
            mmid = real_data['payload'][0]['meeting_info']['meeting_id']
            meeting_code = real_data['payload'][0]['meeting_info']['meeting_code']
            userid = real_data['payload'][0]['meeting_info']['creator']['userid']
            record_file_id = real_data['payload'][0]['recording_files'][0]['record_file_id']
            start_time = real_data['payload'][0]['meeting_info']['start_time']
            end_time = real_data['payload'][0]['meeting_info']['end_time']
        except KeyError:
            logger.info('HandleRecord: Not a completed event')
            return HttpResponse('successfully received callback')
        # 根据code查询会议的日期、标题，拼接待上传的objectKey
        meeting = Meeting.objects.get(mid=meeting_code)
        meeting_type = meeting.meeting_type
        group_name = meeting.group_name
        host_id = meeting.host_id
        objectKey = None
        if group_name == 'MSG':
            objectKey = 'msg/{}.mp4'.format(meeting_code)
        elif group_name == 'Tech':
            objectKey = 'tech/{}.mp4'.format(meeting_code)
        else:
            objectKey = 'sig/{}/{}.mp4'.format(group_name, meeting_code)
        logger.info('objectKey ready to upload to OBS: {}'.format(objectKey))

        # 根据record_file_id查询会议录像的download_url
        download_url = get_video_download(record_file_id, userid)
        if not download_url:
            return JsonResponse({'code': 400, 'msg': '获取下载地址失败'})
        logger.info('download url: {}'.format(download_url))

        # 下载会议录像
        tmpdir = tempfile.gettempdir()
        outfile = os.path.join(tmpdir, '{}.mp4'.format(meeting_code))
        filename = wget.download(download_url, outfile)
        logger.info('temp record file: {}'.format(filename))
        file_size = os.path.getsize(filename)
        if Record.objects.filter(meeting_code=meeting_code, file_size=file_size):
            logger.info('meeting {}: 录像已上传OBS')
            try:
                os.system('rm {}'.format(filename))
            except:
                pass
            return HttpResponse('successfully received callback')

        # 连接OBSClient，上传视频，获取download_url
        access_key_id = os.getenv('MINDSPORE_ACCESS_KEY_ID', '')
        secret_access_key = os.getenv('MINDSPORE_SECRET_ACCESS_KEY', '')
        endpoint = os.getenv('MINDSPORE_OBS_ENDPOINT')
        bucketName = os.getenv('MINDSPORE_OBS_BUCKETNAME')
        if not access_key_id or not secret_access_key or not endpoint or not bucketName:
            logger.error('losing required argements for ObsClient')
            sys.exit(1)
        obs_client = ObsClient(access_key_id=access_key_id,
                               secret_access_key=secret_access_key,
                               server='https://{}'.format(endpoint))
        metadata = {
            "meeting_id": mmid,
            "meeting_code": meeting_code,
            "community": "mindspore",
            "start": start_time,
            "end": end_time
        }
        try:
            res = obs_client.uploadFile(bucketName=bucketName, objectKey=objectKey, uploadFile=filename,
                                        taskNum=10, enableCheckpoint=True, metadata=metadata)
            if res['status'] == 200:
                obs_download_url = 'https://{}.{}/{}?response-content-disposition=attachment'.format(bucketName, endpoint, objectKey)
                logger.info('upload to OBS successfully, the download_url is {}'.format(obs_download_url))
                # 发送包含download_url的邮件
                from meetings.utils.send_recording_completed_msg import sendmail
                topic = meeting.topic
                date = meeting.date
                start = meeting.start
                end = meeting.end
                sendmail(topic, group_name, date, start, end, meeting_code, obs_download_url)
                Record.objects.create(meeting_code=meeting_code, file_size=file_size, download_url=obs_download_url)
                try:
                    os.system('rm {}'.format(filename))
                except:
                    pass
                return HttpResponse('successfully received callback')
            else:
                logger.error(res.errorCode, res.errorMessage)
        except:
            logger.info(traceback.format_exc())


class ParticipantsView(GenericAPIView):
    """会议参会者信息"""
    permission_classes = (QueryPermission,)

    def get(self, request, *args, **kwargs):
        mid = self.kwargs.get('mid')
        meeting = Meeting.objects.filter(mid=mid)
        if not meeting:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        mmid = meeting.values()[0]['mmid']
        host_id = meeting.values()[0]['host_id']
        uri = '/v1/meetings/{}/participants?userid={}'.format(mmid, host_id)
        url = get_url(uri)
        signature, headers = get_signature('GET', uri, "")
        r = requests.get(url, headers=headers)
        return JsonResponse(r.json())
