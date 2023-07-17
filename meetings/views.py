import datetime
import json
import math
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
from rest_framework import status
from rest_framework.filters import SearchFilter
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin, ListModelMixin, RetrieveModelMixin, \
    DestroyModelMixin
from rest_framework.response import Response
from rest_framework_simplejwt import authentication
from rest_framework_simplejwt.tokens import RefreshToken
from meetings.models import Meeting, Record, Activity, ActivityCollect, ActivityRegister, ActivitySign
from meetings.permissions import MaintainerPermission, AdminPermission, QueryPermission, SponsorPermission, \
    ActivityAdminPermission
from meetings.models import GroupUser, Group, User, Collect, Feedback, City, CityUser
from meetings.serializers import LoginSerializer, UsersInGroupSerializer, SigsSerializer, GroupsSerializer, \
    GroupUserAddSerializer, GroupUserDelSerializer, UserInfoSerializer, UserGroupSerializer, MeetingSerializer, \
    MeetingDelSerializer, MeetingDetailSerializer, MeetingsListSerializer, CollectSerializer, FeedbackSerializer, \
    CitiesSerializer, CityUserAddSerializer, CityUserDelSerializer, UserCitySerializer, SponsorSerializer, \
    ActivitySerializer, ActivityUpdateSerializer, ActivityDraftUpdateSerializer, ActivitiesSerializer, \
    ActivityRetrieveSerializer, ActivityCollectSerializer, ActivityRegisterSerializer, ActivitySignSerializer, \
    ActivityRegistrantsSerializer, ApplicantInfoSerializer
from meetings.send_email import sendmail
from meetings.utils.tecent_apis import *
from meetings.utils import send_feedback, prepare_create_activity, send_applicants_info, gene_wx_code, gene_sign_code
from obs import ObsClient
from meetings.utils import drivers
from meetings.auth import CustomAuthentication

logger = logging.getLogger('log')


def refresh_access(user):
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    User.objects.filter(id=user.id).update(signature=access)
    return access


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


class CityMembersView(GenericAPIView, ListModelMixin):
    """城市组成员列表"""
    serializer_class = UsersInGroupSerializer
    queryset = User.objects.all()
    filter_backends = [SearchFilter]
    search_fields = ['nickname']

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        try:
            city_name = self.request.GET.get('city')
            if City.objects.filter(name=city_name):
                city_id = City.objects.get(name=city_name).id
                cityUsers = CityUser.objects.filter(city_id=city_id)
                ids = [x.user_id for x in cityUsers]
                user = User.objects.filter(id__in=ids)
                return user
        except KeyError:
            pass


class NonCityMembersView(GenericAPIView, ListModelMixin):
    """非城市组成员列表"""
    serializer_class = UsersInGroupSerializer
    queryset = User.objects.all()
    filter_backends = [SearchFilter]
    search_fields = ['nickname']

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        try:
            city_name = self.request.GET.get('city')
            if City.objects.filter(name=city_name):
                city_id = City.objects.get(name=city_name).id
                cityUsers = CityUser.objects.filter(city_id=city_id)
                ids = [x.user_id for x in cityUsers]
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


class CitiesView(GenericAPIView, ListModelMixin):
    """城市列表"""
    serializer_class = CitiesSerializer
    queryset = City.objects.all()

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class AddCityView(GenericAPIView, CreateModelMixin):
    """添加城市"""
    serializer_class = CitiesSerializer
    queryset = City.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (AdminPermission,)

    def post(self, request, *args, **kwargs):
        access = refresh_access(self.request.user)
        data = self.request.data
        name = data.get('name')
        if name in City.objects.all().values_list('name', flat=True):
            return JsonResponse({'code': 400, 'msg': '城市名重复', 'access': access})
        etherpad = 'https://etherpad.mindspore.cn/p/meetings-MSG/{}'.format(name)
        City.objects.create(name=name, etherpad=etherpad)
        return JsonResponse({'code': 201, 'msg': '添加成功', 'access': access})


class GroupUserAddView(GenericAPIView, CreateModelMixin):
    """批量新增成员"""
    serializer_class = GroupUserAddSerializer
    queryset = GroupUser.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (AdminPermission,)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        access = refresh_access(self.request.user)
        data = serializer.data
        data['access'] = access
        response = Response()
        response.data = data
        response.status = status.HTTP_201_CREATED
        response.headers = headers
        return response


class GroupUserDelView(GenericAPIView, CreateModelMixin):
    """批量删除组成员"""
    serializer_class = GroupUserDelSerializer
    queryset = GroupUser.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (AdminPermission,)

    def post(self, request, *args, **kwargs):
        group_id = self.request.data.get('group_id')
        ids = self.request.data.get('ids')
        ids_list = [int(x) for x in ids.split('-')]
        GroupUser.objects.filter(group_id=group_id, user_id__in=ids_list).delete()
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 204, 'msg': '删除成功', 'access': access})


class CityUserAddView(GenericAPIView, CreateModelMixin):
    """批量新增城市组成员"""
    serializer_class = CityUserAddSerializer
    queryset = GroupUser.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (AdminPermission,)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        access = refresh_access(self.request.user)
        data = serializer.data
        data['access'] = access
        response = Response()
        response.data = data
        response.status = status
        response.headers = headers
        return response


class CityUserDelView(GenericAPIView, CreateModelMixin):
    """批量删除城市组组成员"""
    serializer_class = CityUserDelSerializer
    queryset = GroupUser.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (AdminPermission,)

    def post(self, request, *args, **kwargs):
        city_id = self.request.data.get('city_id')
        ids = self.request.data.get('ids')
        ids_list = [int(x) for x in ids.split('-')]
        CityUser.objects.filter(city_id=city_id, user_id__in=ids_list).delete()
        for user_id in ids_list:
            if not CityUser.objects.filter(user_id=user_id):
                GroupUser.objects.filter(group_id=1, user_id=int(user_id)).delete()
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 204, 'msg': '删除成功', 'access': access})


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


class UserCityView(GenericAPIView, ListModelMixin):
    """查询用户所在城市组"""
    serializer_class = UserCitySerializer
    queryset = CityUser.objects.all()

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        try:
            usercity = CityUser.objects.filter(user_id=self.kwargs['pk']).all()
            return usercity
        except KeyError:
            pass


class UpdateUserInfoView(GenericAPIView, UpdateModelMixin):
    """修改用户信息"""
    serializer_class = UserInfoSerializer
    queryset = User.objects.all()
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (AdminPermission,)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        access = refresh_access(self.request.user)
        data = serializer.data
        data['access'] = access
        response = Response()
        response.data = data
        return response


class CreateMeetingView(GenericAPIView, CreateModelMixin):
    """预定会议"""
    serializer_class = MeetingSerializer
    queryset = Meeting.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MaintainerPermission,)

    def post(self, *args, **kwargs):
        data = self.request.data
        platform = data['platform'] if 'platform' in data else 'tencent'
        platform = platform.lower()
        host_list = settings.MINDSPORE_MEETING_HOSTS[platform]
        topic = data['topic']
        sponsor = data['sponsor']
        meeting_type = data['meeting_type']
        date = data['date']
        start = data['start']
        end = data['end']
        etherpad = data['etherpad']
        group_name = data['group_name']
        community = 'mindspore'
        city = data['city'] if 'city' in data else None
        emaillist = data['emaillist'] if 'emaillist' in data else None
        agenda = data['agenda'] if 'agenda' in data else None
        record = data['record'] if 'record' in data else None
        user_id = self.request.user.id
        access = refresh_access(self.request.user)
        if meeting_type == 2 and not city:
            return JsonResponse({'code': 400, 'msg': 'MSG会议的城市不能为空', 'access': access})
        if not Group.objects.filter(name=group_name):
            return JsonResponse({'code': 400, 'msg': '错误的group_name', 'access': access})
        group_id = Group.objects.get(name=group_name).id
        # 根据时间判断当前可用host，并选择host
        start_time = date + ' ' + start
        end_time = date + ' ' + end
        if start_time < datetime.datetime.now().strftime('%Y-%m-%d %H:%M'):
            logger.warning('The start time should not be earlier than the current time.')
            return JsonResponse({'code': 1005, 'message': '请输入正确的开始时间', 'access': access})
        if start >= end:
            logger.warning('The end time must be greater than the start time.')
            return JsonResponse({'code': 1001, 'message': '请输入正确的结束时间', 'access': access})
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
            return JsonResponse({'code': 1000, 'message': '时间冲突，请调整时间预定会议！', 'access': access})
        # 从available_host_id中随机生成一个host_id,并在host_dict中取出
        host_id = random.choice(available_host_id)
        logger.info('host_id: {}'.format(host_id))
        status, resp = drivers.createMeeting(platform, date, start, end, topic, host_id, record)
        if status == 200:
            meeting_id = resp['mmid']
            meeting_code = resp['mid']
            join_url = resp['join_url']
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
                group_id=group_id,
                city=city,
                mplatform=platform
            )
            logger.info('{} has created a {} meeting which mid is {}.'.format(sponsor, platform, meeting_code))
            logger.info('meeting info: {},{}-{},{}'.format(date, start, end, topic))
            # 发送邮件
            p1 = Process(target=sendmail, args=(meeting_code, record))
            p1.start()
            meeting_id = Meeting.objects.get(mid=meeting_code).id
            return JsonResponse({'code': 201, 'msg': '创建成功', 'id': meeting_id, 'access': access})
        else:
            return JsonResponse({'code': 400, 'msg': '创建失败', 'access': access})


class CancelMeetingView(GenericAPIView, UpdateModelMixin):
    """取消会议"""
    serializer_class = MeetingDelSerializer
    queryset = Meeting.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MaintainerPermission,)

    def put(self, *args, **kwargs):
        user_id = self.request.user.id
        mid = self.kwargs.get('mmid')
        access = refresh_access(self.request.user)
        if not Meeting.objects.filter(mid=mid, user_id=user_id, is_delete=0) and User.objects.get(id=user_id).level != 3:
            return JsonResponse({'code': 400, 'msg': '会议不存在', 'access': access})
        status = drivers.cancelMeeting(mid)
        meeting = Meeting.objects.get(mid=mid)
        # 数据库更改Meeting的is_delete=1
        if status == 200:
            # 发送删除通知邮件
            from meetings.utils.send_cancel_email import sendmail
            sendmail(mid)

            Meeting.objects.filter(mid=mid).update(is_delete=1)
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
            return JsonResponse({'code': 200, 'msg': '取消会议', 'access': access})
        else:
            logger.error('删除会议失败')
            return JsonResponse({'code': 400, 'msg': '取消失败', 'access': access})

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
    serializer_class = MeetingsListSerializer
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
    authentication_classes = (CustomAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        user_id = self.request.user.id
        meeting_id = self.request.data['meeting']
        access = refresh_access(self.request.user)
        if not meeting_id:
            return JsonResponse({'code': 400, 'msg': 'meeting不能为空', 'access': access})
        if not Collect.objects.filter(meeting_id=meeting_id, user_id=user_id):
            Collect.objects.create(meeting_id=meeting_id, user_id=user_id)
        collection_id = Collect.objects.get(meeting_id=meeting_id, user_id=user_id).id
        return JsonResponse({'code': 201, 'msg': '收藏成功', 'collection_id': collection_id, 'access':
            access})


class CollectionDelView(GenericAPIView, DestroyModelMixin):
    """取消收藏会议"""
    serializer_class = CollectSerializer
    queryset = Collect.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        access = refresh_access(self.request.user)
        response = Response()
        response.data = {'access': access}
        response.status = status.HTTP_204_NO_CONTENT
        return response

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
    authentication_classes = (CustomAuthentication,)

    def post(self, request, *args, **kwargs):
        data = self.request.data
        access = refresh_access(self.request.user)
        try:
            feedback_type = data['feedback_type']
            feedback_content = data['feedback_content']
            feedback_email = data['feedback_email']
            if not re.match(r'^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$', feedback_email):
                return JsonResponse({'code': 400, 'msg': '请填入正确的收件邮箱', 'access': access})
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
            return JsonResponse({'code': 201, 'msg': '反馈意见已收集', 'access': access})
        except KeyError:
            return JsonResponse(
                {'code': 400, 'msg': 'feedback_type, feedback_content and feedback_email are all required!',
                    'access': access})


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
                obs_download_url = 'https://{}.{}/{}?response-content-disposition=attachment'.format(bucketName,
                                                                                                     endpoint,
                                                                                                     objectKey)
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
        if not Meeting.objects.filter(mid=mid, is_delete=0):
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        status, res = drivers.getParticipants(mid)
        if status == 200:
            return JsonResponse(res)
        resp = JsonResponse(res)
        resp.status_code = 400
        return resp


class SponsorsView(GenericAPIView, ListModelMixin):
    """活动发起人列表"""
    serializer_class = SponsorSerializer
    queryset = User.objects.filter(activity_level=2)
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class NonSponsorsView(GenericAPIView, ListModelMixin):
    """非活动发起人列表"""
    serializer_class = SponsorSerializer
    queryset = User.objects.filter(activity_level=1)
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class SponsorsAddView(GenericAPIView, CreateModelMixin):
    """批量添加活动发起人"""
    queryset = User.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def post(self, request, *args, **kwargs):
        ids = self.request.data.get('ids')
        ids_list = [int(x) for x in ids.split('-')]
        User.objects.filter(id__in=ids_list, activity_level=1).update(activity_level=2)
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 201, 'msg': '添加成功', 'access': access})


class SponsorsDelView(GenericAPIView, CreateModelMixin):
    """批量删除活动发起人"""
    queryset = GroupUser.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def post(self, request, *args, **kwargs):
        ids = self.request.data.get('ids')
        ids_list = [int(x) for x in ids.split('-')]
        User.objects.filter(id__in=ids_list, activity_level=2).update(activity_level=1)
        return JsonResponse({'code': 204, 'msg': '删除成功', 'access': access})


class ActivityCreateView(GenericAPIView, CreateModelMixin):
    """创建活动并申请发布"""
    serializer_class = ActivitySerializer
    queryset = Activity.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def post(self, request, *args, **kwargs):
        data = self.request.data
        access = refresh_access(self.request.user)
        title = data['title']
        start_date = data['start_date']
        end_date = data['end_date']
        activity_category = data['activity_category']
        activity_type = data['activity_type']
        address = data.get('address', None)
        detail_address = data.get('detail_address', None)
        longitude = data.get('longitude', None)
        latitude = data.get('latitude', None)
        register_method = data['register_method']
        online_url = data.get('online_url', None)
        register_url = data.get('register_url', None)
        synopsis = data.get('synopsis', None)
        schedules = data['schedules']
        poster = data['poster']
        user_id = self.request.user.id
        publish = self.request.GET.get('publish')

        res = prepare_create_activity.prepare(start_date, end_date, activity_category, activity_type, address,
                                              detail_address, register_method, register_url)
        if res:
            return JsonResponse(res)
        # 创建并申请发布
        if publish and publish.lower() == 'true':
            Activity.objects.create(
                title=title,
                start_date=start_date,
                end_date=end_date,
                activity_category=activity_category,
                activity_type=activity_type,
                address=address,
                detail_address=detail_address,
                longitude=longitude,
                latitude=latitude,
                register_method=register_method,
                online_url=online_url,
                register_url=register_url,
                synopsis=synopsis,
                schedules=json.dumps(schedules),
                poster=poster,
                status=2,
                user_id=user_id
            )
            return JsonResponse({'code': 201, 'msg': '活动申请发布成功！', 'access': access})
        # 创建活动草案
        Activity.objects.create(
            title=title,
            start_date=start_date,
            end_date=end_date,
            activity_category=activity_category,
            activity_type=activity_type,
            address=address,
            detail_address=detail_address,
            longitude=longitude,
            latitude=latitude,
            register_method=register_method,
            online_url=online_url,
            register_url=register_url,
            synopsis=synopsis,
            schedules=json.dumps(schedules),
            poster=poster,
            user_id=user_id,
        )
        return JsonResponse({'code': 201, 'msg': '活动草案创建成功！', 'access': access})


class ActivityUpdateView(GenericAPIView, UpdateModelMixin):
    """修改活动"""
    serializer_class = ActivityUpdateSerializer
    queryset = Activity.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        access = refresh_access(self.request.user)
        data = serializer.data
        data['access'] = access
        response = Response()
        response.data = data
        return response

    def get_queryset(self):
        user_id = self.request.user.id
        activity_level = User.objects.get(id=user_id).activity_level
        queryset = Activity.objects.filter(is_delete=0, status__in=[3, 4, 5], user_id=self.request.user.id)
        if activity_level == 3:
            queryset = Activity.objects.filter(is_delete=0, status__in=[3, 4, 5])
        return queryset


class DraftUpdateView(GenericAPIView, UpdateModelMixin):
    """修改活动草案"""
    serializer_class = ActivityDraftUpdateSerializer
    queryset = Activity.objects.filter(is_delete=0, status=1)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def put(self, request, *args, **kwargs):
        access = refresh_access(self.request.user)
        activity_id = self.kwargs.get('pk')
        data = self.request.data
        title = data['title']
        start_date = data['start_date']
        end_date = data['end_date']
        activity_category = data['activity_category']
        activity_type = data['activity_type']
        address = data.get('address', None)
        detail_address = data.get('detail_address', None)
        longitude = data.get('longitude', None)
        latitude = data.get('latitude', None)
        register_method = data['register_method']
        online_url = data.get('online_url', None)
        register_url = data.get('register_url', None)
        synopsis = data.get('synopsis', None)
        schedules = data['schedules']
        poster = data['poster']
        user_id = self.request.user.id
        publish = self.request.GET.get('publish')
        res = prepare_create_activity.prepare(start_date, end_date, activity_category, activity_type, address,
                                              detail_address, register_method, register_url)
        if res:
            return JsonResponse(res)
        # 修改活动草案并申请发布
        if publish and publish.lower() == 'true':
            Activity.objects.filter(id=activity_id, user_id=user_id).update(
                title=title,
                start_date=start_date,
                end_date=end_date,
                activity_category=activity_category,
                activity_type=activity_type,
                address=address,
                detail_address=detail_address,
                longitude=longitude,
                latitude=latitude,
                register_method=register_method,
                online_url=online_url,
                register_url=register_url,
                synopsis=synopsis,
                schedules=json.dumps(schedules),
                poster=poster,
                status=2
            )
            return JsonResponse({'code': 201, 'msg': '修改活动草案并申请发布成功！', 'access': access})
        # 修改活动草案并保存
        Activity.objects.filter(id=activity_id, user_id=user_id).update(
            title=title,
            start_date=start_date,
            end_date=end_date,
            activity_category=activity_category,
            activity_type=activity_type,
            address=address,
            detail_address=detail_address,
            longitude=longitude,
            latitude=latitude,
            register_method=register_method,
            online_url=online_url,
            register_url=register_url,
            synopsis=synopsis,
            schedules=json.dumps(schedules),
            poster=poster,
        )
        return JsonResponse({'code': 201, 'msg': '修改并保存活动草案', 'access': access})


class WaitingActivities(GenericAPIView, ListModelMixin):
    """待审活动列表"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.filter(is_delete=0, status=2)
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class WaitingActivity(GenericAPIView, RetrieveModelMixin):
    """待审活动详情"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.filter(is_delete=0, status=2)
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class ApproveActivityView(GenericAPIView, UpdateModelMixin):
    """通过审核"""
    queryset = Activity.objects.filter(is_delete=0, status=2)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def put(self, request, *args, **kwargs):
        access = refresh_access(self.request.user)
        activity_id = self.kwargs.get('pk')
        appid = settings.MINDSPORE_APP_CONF['appid']
        secret = settings.MINDSPORE_APP_CONF['secret']
        if activity_id in self.queryset.values_list('id', flat=True):
            logger.info('活动id: {}'.format(activity_id))
            img_url = gene_wx_code.run(appid, secret, activity_id)
            logger.info('生成活动页面二维码: {}'.format(img_url))
            sign_url = gene_sign_code.run(appid, secret, activity_id)
            logger.info('生成活动签到二维码: {}'.format(sign_url))
            Activity.objects.filter(id=activity_id, status=2).update(status=3, wx_code=img_url, sign_url=sign_url)
            return JsonResponse({'code': 201, 'msg': '活动通过审核', 'access': access})
        else:
            return JsonResponse({'code': 400, 'msg': '活动不存在', 'access': access})


class DenyActivityView(GenericAPIView, UpdateModelMixin):
    """驳回申请"""
    queryset = Activity.objects.filter(is_delete=0, status=2)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def put(self, request, *args, **kwargs):
        access = refresh_access(self.request.user)
        activity_id = self.kwargs.get('pk')
        if activity_id in self.queryset.values_list('id', flat=True):
            Activity.objects.filter(id=activity_id, status=2).update(status=1)
            return JsonResponse({'code': 201, 'msg': '活动申请已驳回', 'access': access})
        else:
            return JsonResponse({'code': 400, 'msg': '活动不存在', 'access': access})


class ActivityDeleteView(GenericAPIView, UpdateModelMixin):
    """删除活动"""
    queryset = Activity.objects.filter(is_delete=0, status__gt=2)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def put(self, request, *args, **kwargs):
        access = refresh_access(self.request.user)
        activity_id = self.kwargs.get('pk')
        Activity.objects.filter(id=activity_id).update(is_delete=1)
        return JsonResponse({'code': 204, 'msg': '成功删除活动', 'access': access})


class DraftView(GenericAPIView, RetrieveModelMixin, DestroyModelMixin):
    """查询、删除活动草案"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        access = refresh_access(self.request.user)
        response = Response()
        response.data = {'access': access}
        response.status = status.HTTP_204_NO_CONTENT
        return response

    def get_queryset(self):
        queryset = Activity.objects.filter(is_delete=0, status=1, user_id=self.request.user.id).order_by('-start_date',
                                                                                                         'id')
        return queryset


class ActivitiesListView(GenericAPIView, ListModelMixin):
    """活动列表"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.filter(is_delete=0, status__gt=2).order_by('-start_date', 'id')

    def get(self, request, *args, **kwargs):
        activity_status = self.request.GET.get('activity_status')
        activity_category = self.request.GET.get('activity_category')
        if activity_category and int(activity_category) in range(1, 5):
            if not activity_status:
                self.queryset = self.queryset.filter(activity_category=int(activity_category))
            else:
                if activity_status == 'registering':
                    self.queryset = self.queryset.filter(activity_category=int(activity_category), status__in=[3, 4])
                elif activity_status == 'going':
                    self.queryset = self.queryset.filter(activity_category=int(activity_category), status=4)
                elif activity_status == 'completed':
                    self.queryset = self.queryset.filter(activity_category=int(activity_category), status=5)
        else:
            if activity_status:
                if activity_status == 'registering':
                    self.queryset = self.queryset.filter(status__in=[3, 4])
                elif activity_status == 'going':
                    self.queryset = self.queryset.filter(status=4)
                elif activity_status == 'completed':
                    self.queryset = self.queryset.filter(status=5)
        return self.list(request, *args, **kwargs)


class RecentActivitiesView(GenericAPIView, ListModelMixin):
    """最近的活动列表"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.filter(is_delete=0)

    def get(self, request, *args, **kwargs):
        self.queryset = self.queryset.filter(status__gt=2, start_date__gte=datetime.datetime.now(). \
                                             strftime('%Y-%m-%d')).order_by('-start_date', 'id')
        return self.list(request, *args, **kwargs)


class ActivityDetailView(GenericAPIView, RetrieveModelMixin):
    """活动详情"""
    serializer_class = ActivityRetrieveSerializer
    queryset = Activity.objects.filter(is_delete=0, status__gt=2)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class DraftsListView(GenericAPIView, ListModelMixin):
    """活动草案列表(草稿箱)"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.all()
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (SponsorPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Activity.objects.filter(is_delete=0, status=1, user_id=self.request.user.id).order_by('-start_date',
                                                                                                         'id')
        return queryset


class PublishedActivitiesView(GenericAPIView, ListModelMixin):
    """我发布的活动列表(已发布)"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.all()
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (SponsorPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Activity.objects.filter(is_delete=0, status__gt=2, user_id=self.request.user.id)
        if self.request.user.activity_level == 3:
            queryset = Activity.objects.filter(is_delete=0, status__gt=2)
        return queryset


class WaitingPublishingActivitiesView(GenericAPIView, ListModelMixin):
    """待发布的活动列表(待发布)"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.all()
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (SponsorPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Activity.objects.filter(is_delete=0, status=2, user_id=self.request.user.id).order_by('-start_date', 'id')
        return queryset


class ActivityCollectView(GenericAPIView, CreateModelMixin):
    """收藏活动"""
    serializer_class = ActivityCollectSerializer
    queryset = ActivityCollect.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)

    def post(self, request, *args, **kwargs):
        user_id = self.request.user.id
        activity_id = self.request.data['activity']
        ActivityCollect.objects.create(activity_id=activity_id, user_id=user_id)
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 201, 'msg': '收藏活动', 'access': access})


class ActivityCollectionsView(GenericAPIView, ListModelMixin):
    """收藏活动列表"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (authentication.JWTAuthentication,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        user_id = self.request.user.id
        collection_lst = ActivityCollect.objects.filter(user_id=user_id).values_list('activity', flat=True)
        queryset = Activity.objects.filter(is_delete=0, id__in=collection_lst).order_by('-start_date', 'id')
        return queryset


class ActivityCollectionDelView(GenericAPIView, DestroyModelMixin):
    """取消收藏活动"""
    serializer_class = ActivityCollectSerializer
    queryset = ActivityCollect.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        access = refresh_access(self.request.user)
        response = Response()
        response.data = {'access': access}
        response.status = status.HTTP_204_NO_CONTENT
        return response

    def get_queryset(self):
        queryset = ActivityCollect.objects.filter(user_id=self.request.user.id)
        return queryset


class ActivityRegisterView(GenericAPIView, CreateModelMixin):
    """活动报名"""
    serializer_class = ActivityRegisterSerializer
    queryset = ActivityRegister.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)

    def post(self, request, *args, **kwargs):
        access = refresh_access(self.request.user)
        data = self.request.data
        activity_id = data['activity']
        user_id = self.request.user.id
        if Activity.objects.filter(id=activity_id, user_id=user_id):
            return JsonResponse({'code': 400, 'msg': '不能报名自己发起的活动', 'access': access})
        name = data['name']
        wx_account = data['wx_account']
        gender = data['gender']
        age = data['age']
        gitee_id = data.get('gitee_id', None)
        telephone = data['telephone']
        email = data['email']
        company = data['company']
        career_direction = data['career_direction']
        profession = data['profession']
        working_years = data['working_years']
        register_number = User.objects.get(id=self.request.user.id).register_number
        register_number += 1
        User.objects.filter(id=self.request.user.id).update(
            name=name,
            wx_account=wx_account,
            gender=gender,
            age=age,
            gitee_name=gitee_id,
            telephone=telephone,
            email=email,
            company=company,
            career_direction=career_direction,
            profession=profession,
            working_years=working_years
        )
        ActivityRegister.objects.create(activity_id=activity_id, user_id=user_id)
        register_number = len(ActivityRegister.objects.filter(user_id=self.request.user.id))
        return JsonResponse({'code': 201, 'msg': '报名成功', 'register_number': register_number, 'access': access})


class RegisteredActivitiesView(GenericAPIView, ListModelMixin):
    """已报名的活动(已报名)"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (authentication.JWTAuthentication,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        user_id = self.request.user.id
        register_lst = ActivityRegister.objects.filter(user_id=user_id).values_list('activity')
        queryset = Activity.objects.filter(is_delete=0, id__in=register_lst).order_by('-start_date', 'id')
        return queryset


class ActivitySignView(GenericAPIView, CreateModelMixin):
    """活动签到"""
    serializer_class = ActivitySignSerializer
    queryset = ActivitySign.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)

    def post(self, request, *args, **kwargs):
        access = refresh_access(self.request.user)
        user_id = self.request.user.id
        activity_id = self.request.data['activity']
        if not ActivityRegister.objects.filter(activity_id=activity_id, user_id=user_id):
            return JsonResponse({'code': 400, 'msg': '用户还没有报名这个活动', 'access': access})
        if not ActivitySign.objects.filter(activity_id=activity_id, user_id=user_id):
            ActivitySign.objects.create(activity_id=activity_id, user_id=user_id)
        return JsonResponse({'code': 201, 'msg': '活动签到', 'access': access})


class ActivityRegistrantsView(GenericAPIView, RetrieveModelMixin):
    """活动报名者信息"""
    serializer_class = ActivityRegistrantsSerializer
    queryset = Activity.objects.filter(is_delete=0)
    permission_classes = (QueryPermission,)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class ApplicantsInfoView(GenericAPIView, ListModelMixin):
    """活动报名者信息列表"""
    queryset = ActivityRegister.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)

    def post(self, request, *args, **kwargs):
        access = refresh_access(self.request.user)
        data = self.request.data
        try:
            activity_id = data['activity']
            mailto = data['mailto']
            if not re.match(r'^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$', mailto):
                return JsonResponse({'code': 400, 'msg': '请填入正确的收件邮箱', 'access': access})
            user_id = self.request.user.id
            if not Activity.objects.filter(id=activity_id, user_id=user_id) and User.objects.get(
                    id=user_id).activity_level != 3:
                return JsonResponse({'code': 403, 'msg': '无权查看该活动的报名列表', 'access': access})
            self.queryset = ActivityRegister.objects.filter(activity_id=activity_id)
            send_applicants_info.run(self.queryset, mailto)
            return JsonResponse({'code': '200', 'msg': '已发送活动报名信息', 'access': access})
        except KeyError:
            return JsonResponse({'code': 400, 'msg': '需要activity和mailto两个参数', 'access': access})


class ApplicantInfoView(GenericAPIView, RetrieveModelMixin):
    """活动报名者信息详情"""
    serializer_class = ApplicantInfoSerializer
    queryset = User.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (authentication.JWTAuthentication,)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class CountActivitiesView(GenericAPIView, ListModelMixin):
    """各类活动计数"""
    queryset = Activity.objects.filter(is_delete=0, status__gt=2).order_by('-start_date', 'id')
    filter_backends = [SearchFilter]
    search_fields = ['title']

    def get(self, request, *args, **kwargs):
        search = self.request.GET.get('search')
        activity_category = self.request.GET.get('activity_category')
        if search and not activity_category:
            self.queryset = self.queryset.filter(title__icontains=search)
        elif not search and activity_category:
            try:
                if int(activity_category) in range(1, 5):
                    self.queryset = self.queryset.filter(activity_category=int(activity_category))
            except (TypeError, ValueError):
                pass
        else:
            try:
                if int(activity_category) in range(1, 5):
                    self.queryset = self.queryset.filter(activity_category=int(activity_category)).filter(
                        title__icontains=search)
                else:
                    self.queryset = self.queryset.filter(title__icontains=search)
            except (TypeError, ValueError):
                pass
        all_activities_count = len(self.queryset.filter(is_delete=0, status__gt=2).values())
        registering_activities_count = len(self.queryset.filter(is_delete=0, status__in=[3, 4]).values())
        going_activities_count = len(self.queryset.filter(is_delete=0, status=4).values())
        completed_activities_count = len(self.queryset.filter(is_delete=0, status=5).values())
        res = {'all_activities_count': all_activities_count,
               'registering_activities_count': registering_activities_count,
               'going_activities_count': going_activities_count,
               'completed_activities_count': completed_activities_count}
        return JsonResponse(res)


class MyCountsView(GenericAPIView, ListModelMixin):
    """我的各类计数"""
    queryset = Activity.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (authentication.JWTAuthentication,)

    def get(self, request, *args, **kwargs):
        user_id = self.request.user.id
        user = User.objects.get(id=user_id)
        level = user.level
        activity_level = user.activity_level

        # shared
        collected_meetings_count = len(Meeting.objects.filter(is_delete=0, id__in=(
            Collect.objects.filter(user_id=user_id).values_list('meeting_id', flat=True))).values())
        collected_activities_count = len(Activity.objects.filter(is_delete=0, id__in=(
            ActivityCollect.objects.filter(user_id=user_id).values_list('activity_id', flat=True))).values())
        registerd_activities_count = len(Activity.objects.filter(is_delete=0, status__gt=2, id__in=(
            ActivityRegister.objects.filter(user_id=user_id).values_list('activity_id', flat=True))).values())
        res = {'collected_meetings_count': collected_meetings_count,
               'collected_activities_count': collected_activities_count,
               'registerd_activities_count': registerd_activities_count}
        # permission limited
        if level == 2:
            created_meetings_count = len(Meeting.objects.filter(is_delete=0, user_id=user_id).values())
            res['created_meetings_count'] = created_meetings_count
        if level == 3:
            created_meetings_count = len(Meeting.objects.filter(is_delete=0).values())
            res['created_meetings_count'] = created_meetings_count
        if activity_level == 2:
            published_activities_count = len(
                Activity.objects.filter(is_delete=0, status__gt=2, user_id=user_id).values())
            drafts_count = len(Activity.objects.filter(is_delete=0, status=1, user_id=user_id).values())
            publishing_activities_count = len(Activity.objects.filter(is_delete=0, status=2, user_id=user_id).values())
            res['published_activities_count'] = published_activities_count
            res['register_table_count'] = published_activities_count
            res['drafts_count'] = drafts_count
            res['publishing_activities_count'] = publishing_activities_count
        if activity_level == 3:
            published_activities_count = len(Activity.objects.filter(is_delete=0, status__gt=2).values())
            drafts_count = len(Activity.objects.filter(is_delete=0, status=1, user_id=user_id).values())
            publishing_activities_count = len(Activity.objects.filter(is_delete=0, status=2).values())
            res['published_activities_count'] = published_activities_count
            res['register_table_count'] = published_activities_count
            res['drafts_count'] = drafts_count
            res['publishing_activities_count'] = publishing_activities_count
        return JsonResponse(res)


class TicketView(GenericAPIView, RetrieveModelMixin):
    """查看活动门票"""
    queryset = Activity.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (authentication.JWTAuthentication,)

    def get(self, request, *args, **kwargs):
        activity_id = self.kwargs.get('pk')
        user_id = self.request.user.id
        if not ActivityRegister.objects.filter(activity_id=activity_id, user_id=user_id):
            return JsonResponse({'code': 404, 'msg': '用户还没有报名这个活动'})
        res = {
            'title': self.queryset.get(id=activity_id).title,
            'poster': self.queryset.get(id=activity_id).poster,
            'name': User.objects.get(id=user_id).name,
            'telephone': User.objects.get(id=user_id).telephone,
            'activity_id': activity_id
        }
        return JsonResponse(res)


class MeetingsDataView(GenericAPIView, ListModelMixin):
    """会议日历数据"""
    queryset = Meeting.objects.filter(is_delete=0).order_by('start')

    def get(self, request, *args, **kwargs):
        self.queryset = self.queryset.filter(
            date__gte=(datetime.datetime.now() - datetime.timedelta(days=180)).strftime('%Y-%m-%d'),
            date__lte=(datetime.datetime.now() + datetime.timedelta(days=180)).strftime('%Y-%m-%d'))
        queryset = self.filter_queryset(self.get_queryset()).values()
        tableData = []
        date_list = []
        for query in queryset:
            date_list.append(query.get('date'))
        date_list = sorted(list(set(date_list)))
        for date in date_list:
            tableData.append(
                {
                    'date': date,
                    'timeData': [{
                        'id': meeting.id,
                        'group_name': meeting.group_name,
                        'meeting_type': meeting.meeting_type,
                        'city': meeting.city,
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
                        'replay_url': meeting.replay_url,
                        'platform': meeting.mplatform
                    } for meeting in Meeting.objects.filter(is_delete=0, date=date)]
                })
        return Response({'tableData': tableData})


class ActivitiesDataView(GenericAPIView, ListModelMixin):
    """活动日历数据"""
    queryset = Activity.objects.filter(is_delete=0, status__in=[3, 4, 5])

    def get(self, request, *args, **kwargs):
        self.queryset = self.queryset.filter(
            start_date__gte=(datetime.datetime.now() - datetime.timedelta(days=180)).strftime('%Y-%m-%d'),
            start_date__lte=(datetime.datetime.now() + datetime.timedelta(days=180)).strftime('%Y-%m-%d'))
        queryset = self.filter_queryset(self.get_queryset()).values()
        tableData = []
        date_list = []
        for query in queryset:
            date_list.append(query.get('start_date'))
        date_list = sorted(list(set(date_list)))
        for start_date in date_list:
            tableData.append(
                {
                    'start_date': start_date,
                    'timeData': [{
                        'id': activity.id,
                        'title': activity.title,
                        'start_date': activity.start_date,
                        'end_date': activity.end_date,
                        'activity_category': activity.activity_category,
                        'activity_type': activity.activity_type,
                        'address': activity.address,
                        'detail_address': activity.detail_address,
                        'longitude': activity.longitude,
                        'latitude': activity.latitude,
                        'register_method': activity.register_method,
                        'online_url': activity.online_url,
                        'register_url': activity.register_url,
                        'synopsis': activity.synopsis,
                        'sign_url': activity.sign_url,
                        'replay_url': activity.replay_url,
                        'poster': activity.poster,
                        'wx_code': activity.wx_code,
                        'schedules': json.loads(activity.schedules)
                    } for activity in Activity.objects.filter(is_delete=0, start_date=start_date)]
                }
            )
        return Response({'tableData': tableData})
