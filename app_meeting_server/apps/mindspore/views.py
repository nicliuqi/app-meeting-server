import datetime
import math
from random import random
from django.conf import settings
from multiprocessing import Process
from django.db.models import Q
from django.http import JsonResponse
from rest_framework import permissions
from rest_framework import status
from rest_framework.filters import SearchFilter
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin, ListModelMixin, RetrieveModelMixin, \
    DestroyModelMixin
from rest_framework.response import Response
from rest_framework_simplejwt import authentication
from rest_framework_simplejwt.tokens import RefreshToken
from app_meeting_server.utils import wx_apis
from mindspore.models import Activity, ActivityCollect
from mindspore.permissions import MaintainerPermission, AdminPermission, QueryPermission, \
    SponsorPermission, ActivityAdminPermission
from mindspore.models import GroupUser, Group, User, Collect, City, CityUser
from mindspore.serializers import LoginSerializer, UsersInGroupSerializer, SigsSerializer, \
    GroupsSerializer, GroupUserAddSerializer, GroupUserDelSerializer, UserInfoSerializer, UserGroupSerializer, \
    MeetingSerializer, MeetingDelSerializer, MeetingsListSerializer, CollectSerializer, CitiesSerializer, \
    CityUserAddSerializer, CityUserDelSerializer, UserCitySerializer, SponsorSerializer, ActivitySerializer, \
    ActivityUpdateSerializer, ActivityDraftUpdateSerializer, ActivitiesSerializer, ActivityRetrieveSerializer, \
    ActivityCollectSerializer
from mindspore.send_email import sendmail
from mindspore.utils.tencent_apis import *
from mindspore.utils import gene_wx_code, drivers, send_cancel_email
from mindspore.auth import CustomAuthentication
from app_meeting_server.utils.common import get_cur_date
from app_meeting_server.utils.operation_log import LoggerContext, OperationLogModule, OperationLogDesc, OperationLogType, OperationLogResult

logger = logging.getLogger('log')


def refresh_access(user):
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    User.objects.filter(id=user.id).update(signature=access)
    return access


# ------------------------------user view------------------------------
class LoginView(GenericAPIView, CreateModelMixin, ListModelMixin):
    """用户注册与授权登陆"""
    serializer_class = LoginSerializer
    queryset = User.objects.all()

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_LOGIN,
                           OperationLogDesc.OP_DESC_USER_LOGIN_CODE) as log_context:
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def perform_create(self, serializer):
        serializer.save()


class LogoutView(GenericAPIView):
    """登出"""
    authentication_classes = (CustomAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_LOGOUT,
                           OperationLogDesc.OP_DESC_USER_LOGOFF_CODE) as log_context:
            log_context.log_vars = [request.user.id]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        refresh_access(self.request.user)
        resp = JsonResponse({
            'code': 201,
            'msg': 'User {} logged out'.format(self.request.user.id)
        })
        logger.info('User {} logged out'.format(self.request.user.id))
        return resp


class LogoffView(GenericAPIView):
    """注销"""
    authentication_classes = (CustomAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_LOGOFF,
                           OperationLogDesc.OP_DESC_USER_LOGOFF_CODE) as log_context:
            log_context.log_vars = [request.user.id]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        user_id = self.request.user.id
        cur_date = get_cur_date()
        expired_date = cur_date + datetime.timedelta(days=settings.LOGOFF_EXPIRED)
        User.objects.filter(id=user_id).update(is_delete=1, logoff_time=expired_date)
        resp = JsonResponse({
            'code': 201,
            'msg': 'User {} logged off'.format(user_id)
        })
        logger.info('User {} logged off'.format(user_id))
        return resp


class AgreePrivacyPolicyView(GenericAPIView, UpdateModelMixin):
    """同意隐私声明"""
    authentication_classes = (CustomAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_USER_AGREEMENT_CODE) as log_context:
            log_context.log_vars = [request.user.id]
            ret = self.update(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def update(self, request, *args, **kwargs):
        now_time = datetime.datetime.now()
        access = refresh_access(self.request.user)
        if User.objects.get(id=self.request.user.id).agree_privacy_policy:
            resp = JsonResponse({
                'code': 400,
                'msg': 'The user has signed privacy policy agreement already.',
                'access': access
            })
            resp.status_code = 400
            return resp
        User.objects.filter(id=self.request.user.id).update(agree_privacy_policy=True,
                                                            agree_privacy_policy_time=now_time,
                                                            agree_privacy_policy_version=settings.PRIVACY_POLICY_VERSION)
        resp = JsonResponse({
            'code': 201,
            'msg': 'Updated',
            'access': access
        })
        return resp


class RevokeAgreementView(GenericAPIView):
    """撤销同意隐私声明"""
    authentication_classes = (CustomAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_USER_REVOKEAGREEMENT_CODE) as log_context:
            log_context.log_vars = [request.user.id]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        now_time = datetime.datetime.now()
        refresh_access(self.request.user)
        User.objects.filter(id=self.request.user.id).update(revoke_agreement_time=now_time)
        resp = JsonResponse({
            'code': 201,
            'msg': 'Revoke agreement of privacy policy'
        })
        return resp


class UpdateUserInfoView(GenericAPIView, UpdateModelMixin):
    """修改用户信息"""
    serializer_class = UserInfoSerializer
    queryset = User.objects.all()
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (AdminPermission,)

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_USER_MODIIFY_CODE) as log_context:
            log_context.log_vars = [request.user.id, request.user.id]
            ret = self.update(request, *args, **kwargs)
            log_context.result = ret
            return ret

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


class GroupMembersView(GenericAPIView, ListModelMixin):
    """组成员列表"""
    serializer_class = UsersInGroupSerializer
    queryset = User.objects.all()
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (AdminPermission,)

    def get(self, request, *args, **kwargs):
        group_name = self.request.GET.get('group')
        if not Group.objects.filter(name=group_name):
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        group_name = self.request.GET.get('group')
        group_id = Group.objects.get(name=group_name).id
        groupusers = GroupUser.objects.filter(group_id=group_id)
        ids = [x.user_id for x in groupusers]
        user = User.objects.filter(id__in=ids, is_delete=0)
        return user


class NonGroupMembersView(GenericAPIView, ListModelMixin):
    """非组成员列表"""
    serializer_class = UsersInGroupSerializer
    queryset = User.objects.all()
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (AdminPermission,)

    def get(self, request, *args, **kwargs):
        group_name = self.request.GET.get('group')
        if not Group.objects.filter(name=group_name):
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        group_name = self.request.GET.get('group')
        group_id = Group.objects.get(name=group_name).id
        groupusers = GroupUser.objects.filter(group_id=group_id)
        ids = [x.user_id for x in groupusers]
        user = User.objects.filter(is_delete=0).exclude(id__in=ids)
        return user


class SigsView(GenericAPIView, ListModelMixin):
    """SIG列表"""
    serializer_class = SigsSerializer
    queryset = Group.objects.filter(group_type=1)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


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


class GroupUserAddView(GenericAPIView, CreateModelMixin):
    """批量新增成员"""
    serializer_class = GroupUserAddSerializer
    queryset = GroupUser.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (AdminPermission,)

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_USER_ADD_GROUP_CODE) as log_context:
            log_context.log_vars = [request.data.get("ids"), request.data.get("group_id")]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

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

    def validate(self, request):
        err_msgs = []
        validated_data = {}
        group_id = self.request.data.get('group_id')
        ids = self.request.data.get('ids')
        if not Group.objects.filter(id=group_id):
            err_msgs.append('Group {} is not exist'.format(group_id))
        else:
            validated_data['group_id'] = group_id
        try:
            ids_list = [int(x) for x in ids.split('-')]
            match_queryset = GroupUser.objects.filter(group_id=group_id, user_id__in=ids_list)
            if len(ids_list) != len(match_queryset):
                err_msgs.append('Improper parameter: ids')
            else:
                validated_data['ids_list'] = ids_list
        except ValueError:
            err_msgs.append('Invalid parameter: ids')
        if not err_msgs:
            return True, validated_data
        logger.error('[GroupUserDelView] Fail to validate when deleting groups members, the error messages are {}'.
                     format(','.join(err_msgs)))
        return False, None

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_USER_REMOVE_GROUP_CODE) as log_context:
            log_context.log_vars = [request.data.get("ids"), request.data.get("group_id")]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        is_validated, validated_data = self.validate(request)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        group_id = validated_data.get('group_id')
        ids_list = validated_data.get('ids_list')
        GroupUser.objects.filter(group_id=group_id, user_id__in=ids_list).delete()
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 204, 'msg': '删除成功', 'access': access})


class GroupsView(GenericAPIView, ListModelMixin):
    """组信息"""
    serializer_class = GroupsSerializer
    queryset = Group.objects.all()

    def get(self, request, *args, **kwargs):
        self.queryset = self.queryset.filter(group_type__in=(2, 3))
        return self.list(request, *args, **kwargs)


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


class CityMembersView(GenericAPIView, ListModelMixin):
    """城市组成员列表"""
    serializer_class = UsersInGroupSerializer
    queryset = User.objects.filter(is_delete=0)
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (AdminPermission,)

    def get(self, request, *args, **kwargs):
        city_name = self.request.GET.get('city')
        if not City.objects.filter(name=city_name):
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        city_name = self.request.GET.get('city')
        city_id = City.objects.get(name=city_name).id
        cityUsers = CityUser.objects.filter(city_id=city_id)
        ids = [x.user_id for x in cityUsers]
        user = User.objects.filter(id__in=ids)
        return user


class NonCityMembersView(GenericAPIView, ListModelMixin):
    """非城市组成员列表"""
    serializer_class = UsersInGroupSerializer
    queryset = User.objects.filter(is_delete=0)
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (AdminPermission,)

    def get(self, request, *args, **kwargs):
        city_name = self.request.GET.get('city')
        if City.objects.filter(name=city_name):
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        city_name = self.request.GET.get('city')
        city_id = City.objects.get(name=city_name).id
        cityUsers = CityUser.objects.filter(city_id=city_id)
        ids = [x.user_id for x in cityUsers]
        user = User.objects.filter(is_delete=0).exclude(id__in=ids)
        return user


class SponsorsView(GenericAPIView, ListModelMixin):
    """活动发起人列表"""
    serializer_class = SponsorSerializer
    queryset = User.objects.filter(activity_level=2, is_delete=0)
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class NonSponsorsView(GenericAPIView, ListModelMixin):
    """非活动发起人列表"""
    serializer_class = SponsorSerializer
    queryset = User.objects.filter(activity_level=1, is_delete=0)
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class SponsorsAddView(GenericAPIView, CreateModelMixin):
    """批量添加活动发起人"""
    queryset = User.objects.filter(is_delete=0)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def validate(self, request):
        err_msgs = []
        validated_data = {}
        ids = self.request.data.get('ids')
        try:
            ids_list = [int(x) for x in ids.split('-')]
            match_queryset = User.objects.filter(id__in=ids_list, activity_level=1, is_delete=0)
            if len(ids_list) != len(match_queryset):
                err_msgs.append('Improper parameter: ids')
            else:
                validated_data['ids_list'] = ids_list
        except ValueError:
            err_msgs.append('Invalid parameter: ids')
        if not err_msgs:
            return True, validated_data
        logger.error('[SponsorsAddView] Fail to validate when adding activity sponsors, the error messages are {}'.
                     format(','.join(err_msgs)))
        return False, None

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_USER_ADD_ACTIVITY_SPONSOR_CODE,
                           ) as log_context:
            log_context.log_vars = [request.data.get('ids')]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        is_validated, validated_data = self.validate(request)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        ids_list = validated_data.get('ids_list')
        User.objects.filter(id__in=ids_list, activity_level=1).update(activity_level=2)
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 201, 'msg': '添加成功', 'access': access})


class SponsorsDelView(GenericAPIView, CreateModelMixin):
    """批量删除活动发起人"""
    queryset = GroupUser.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def validate(self, request):
        err_msgs = []
        validated_data = {}
        ids = self.request.data.get('ids')
        try:
            ids_list = [int(x) for x in ids.split('-')]
            match_queryset = User.objects.filter(id__in=ids_list, activity_level=2, is_delete=0)
            if len(ids_list) != len(match_queryset):
                err_msgs.append('Improper parameter: ids')
            else:
                validated_data['ids_list'] = ids_list
        except ValueError:
            err_msgs.append('Invalid parameter: ids')
        if not err_msgs:
            return True, validated_data
        logger.error('[SponsorDelView] Fail to validate when deleting activity sponsors, the error messages are {}'.
                     format(','.join(err_msgs)))
        return False, None

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_USER_REMOVE_ACTIVITY_SPONSOR_CODE) as log_context:
            log_context.log_vars = [request.data.get('ids')]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        is_validated, validated_data = self.validate(request)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        ids_list = validated_data.get('ids_list')
        User.objects.filter(id__in=ids_list, activity_level=2).update(activity_level=1)
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 204, 'msg': '删除成功', 'access': access})


# ------------------------------meeting view------------------------------
class CreateMeetingView(GenericAPIView, CreateModelMixin):
    """预定会议"""
    serializer_class = MeetingSerializer
    queryset = Meeting.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MaintainerPermission,)

    def validate(self, request):
        now_time = datetime.datetime.now()
        err_msgs = []
        data = self.request.data
        platform = data.get('platform', 'tencent')
        host_list = None
        topic = data.get('topic')
        sponsor = data.get('sponsor')
        meeting_type = data.get('meeting_type')
        date = data.get('date')
        start = data.get('start')
        end = data.get('end')
        etherpad = data.get('etherpad')
        group_name = data.get('group_name')
        community = data.get('community', 'openeuler')
        city = data.get('city')
        emaillist = data.get('emaillist')
        agenda = data.get('agenda')
        record = data.get('record')

        if not isinstance(platform, str):
            err_msgs.append('Field platform must be string type')
        else:
            host_list = settings.MEETING_HOSTS.get(platform.lower())
            if not host_list or not isinstance(host_list, list):
                err_msgs.append('Could not match any meeting host')
        try:
            start_time = datetime.datetime.strptime(' '.join([date, start]), '%Y-%m-%d %H:%M')
            end_time = datetime.datetime.strptime(' '.join([date, end]), '%Y-%m-%d %H:%M')
            if start_time <= now_time:
                err_msgs.append('The start time should not be later than the current time')
            elif (start_time - now_time).days > 60:
                err_msgs.append('The start time is at most 60 days later than the current time')
            if start_time >= end_time:
                err_msgs.append('The start time should not be later than the end time')
        except ValueError:
            err_msgs.append('Invalid start time or end time')
        if meeting_type not in range(1, 4):
            err_msgs.append('Invalid meeting type: {}'.format(meeting_type))
        elif meeting_type == 2 and not city:
            err_msgs.append('MSG Meeting must apply field city')
        if not Group.objects.filter(name=group_name):
            err_msgs.append('Invalid group name: {}'.format(group_name))
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
        validated_data = {
            'platform': platform,
            'host_list': host_list,
            'topic': topic,
            'sponsor': sponsor,
            'meeting_type': meeting_type,
            'date': date,
            'start': start,
            'end': end,
            'etherpad': etherpad,
            'group_name': group_name,
            'communinty': community,
            'city': city,
            'emaillist': emaillist,
            'agenda': agenda,
            'record': record,
            'user_id': request.user.id,
            'group_id': Group.objects.get(group_name=group_name).id
        }
        return True, validated_data

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_MEETING,
                           OperationLogType.OP_TYPE_CREATE,
                           OperationLogDesc.OP_DESC_MEETING_CREATE_CODE) as log_context:
            log_context.log_vars = [request.data.get('topic')]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        is_validated, data = self.validate(request)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        platform = data.get('platform')
        host_list = data.get('host_list')
        topic = data.get('topic')
        sponsor = data.get('sponsor')
        meeting_type = data.get('meeting_type')
        date = data.get('date')
        start = data.get('start')
        end = data.get('end')
        etherpad = data.get('etherpad')
        group_name = data.get('group_name')
        community = data.get('community')
        city = data.get('city')
        emaillist = data.get('emaillist')
        agenda = data.get('agenda')
        record = data.get('record')
        user_id = self.request.user.id
        access = refresh_access(self.request.user)
        group_id = Group.objects.get(name=group_name).id
        # 根据时间判断当前可用host，并选择host
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

    def validate(self, request):
        err_msgs = []
        user_id = self.request.user.id
        mid = self.kwargs.get('mmid')
        if not Meeting.objects.filter(mid=mid, is_delete=0):
            err_msgs.append('Meeting {} is not exist'.format(mid))
        elif not Meeting.objects.filter(mid=mid, user_id=user_id, is_delete=0) or User.objects.get(id=user_id).level != 3:
            err_msgs.append('User {} has no access to delete meeting {}'.format(user_id, mid))
        if not err_msgs:
            return True
        logger.error('[CancelMeetingView] Fail to validate when deleting meeting, the error messages are {}'.
                     format(','.join(err_msgs)))
        return False

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_MEETING,
                           OperationLogType.OP_TYPE_DELETE,
                           OperationLogDesc.OP_DESC_MEETING_DELETE_CODE) as log_context:
            log_context.log_vars = [kwargs.get('mmid')]
            ret = self.update(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def update(self, request, *args, **kwargs):
        if not self.validate(request):
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        mid = self.kwargs.get('mmid')
        status = drivers.cancelMeeting(mid)
        meeting = Meeting.objects.get(mid=mid)
        # 数据库更改Meeting的is_delete=1
        if status != 200:
            logger.error('删除会议失败')
            return JsonResponse({'code': 400, 'msg': '取消失败'})
        # 发送删除通知邮件
        send_cancel_email.sendmail(mid)

        Meeting.objects.filter(mid=mid).update(is_delete=1)
        # 发送会议取消通知
        collections = Collect.objects.filter(meeting_id=meeting.id)
        if collections:
            access_token = wx_apis.get_token()
            topic = meeting.topic
            date = meeting.date
            start_time = meeting.start
            time = date + ' ' + start_time
            for collection in collections:
                user_id = collection.user_id
                user = User.objects.get(id=user_id)
                nickname = user.nickname
                openid = user.openid
                content = wx_apis.get_remove_template(openid, topic, time, mid)
                r = wx_apis.send_subscription(content, access_token)
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
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 200, 'msg': '取消会议', 'access': access})


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
        except Exception:
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

    def validate(self, request):
        err_msgs = []
        validated_data = {}
        user_id = self.request.user.id
        meeting_id = self.request.data.get('meeting')
        if not Meeting.objects.filter(mid=meeting_id, is_delete=0):
            err_msgs.append('Meeting {} is not exist'.format(meeting_id))
        elif Collect.objects.filter(meeting_id=meeting_id, user_id=user_id):
            err_msgs.append('User {} had collected meeting {}'.format(user_id, meeting_id))
        else:
            validated_data['meeting_id'] = meeting_id
        if not err_msgs:
            return True, validated_data
        logger.error('[CollectMeetingView] Fail to validate when creating meetings, the error messages are {}'.format(
            ','.join(err_msgs)))
        return False, None

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_MEETING,
                           OperationLogType.OP_TYPE_COLLECT,
                           OperationLogDesc.OP_DESC_MEETING_COLLECT_CODE) as log_context:
            log_context.log_vars = [request.data.get('meeting')]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        is_validated, validated_data = self.validate(request)
        if not is_validated:
            return JsonResponse({'code': 400, 'Request': 'Bad Request'})
        user_id = self.request.user.id
        meeting_id = validated_data.get('meeting')
        Collect.objects.create(meeting_id=meeting_id, user_id=user_id)
        collection_id = Collect.objects.get(meeting_id=meeting_id, user_id=user_id).id
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 201, 'msg': '收藏成功', 'collection_id': collection_id, 'access': access})


class CollectionDelView(GenericAPIView, DestroyModelMixin):
    """取消收藏会议"""
    serializer_class = CollectSerializer
    queryset = Collect.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def validate(self, request):
        err_msgs = []
        if not Meeting.objects.filter(id=self.kwargs.get('pk'), is_delete=0):
            err_msgs.append('Meeting {} is not exist'.format(self.kwargs.get('pk')))
        if not Collect.objects.filter(meeting_id=self.kwargs.get('pk'), user_id=self.request.user.id):
            err_msgs.append('User {} had not collected meeting {}'.format(self.request.user.id, self.kwargs.get('pk')))
        if not err_msgs:
            return True
        logger.error('[CollectionDelView] Fail to validate when deleting meeting collection, the error messages are {}'.
                     format(','.join(err_msgs)))
        return False

    def delete(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_MEETING,
                           OperationLogType.OP_TYPE_CANCEL_COLLECT,
                           OperationLogDesc.OP_DESC_MEETING_CANCEL_COLLECT_CODE) as log_context:
            log_context.log_vars = [kwargs.get('pk')]
            ret = self.destroy(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def destroy(self, request, *args, **kwargs):
        if not self.validate(request):
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
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


# ------------------------------city view------------------------------
class CitiesView(GenericAPIView, ListModelMixin):
    """城市列表"""
    serializer_class = CitiesSerializer
    queryset = City.objects.all()
    authentication_classes = (authentication.JWTAuthentication,)
    permission_classes = (AdminPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class AddCityView(GenericAPIView, CreateModelMixin):
    """添加城市"""
    serializer_class = CitiesSerializer
    queryset = City.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (AdminPermission,)

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_CITY,
                           OperationLogType.OP_TYPE_CREATE,
                           OperationLogDesc.OP_DESC_CITY_CREATE_CODE) as log_context:
            log_context.log_vars = [request.data.get("name")]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        data = self.request.data
        name = data.get('name')
        if name in City.objects.all().values_list('name', flat=True):
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        etherpad = '{}/p/meetings-MSG/{}'.format(settings.ETHERPAD_PREFIX, name)
        City.objects.create(name=name, etherpad=etherpad)
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 201, 'msg': '添加成功', 'access': access})


class CityUserAddView(GenericAPIView, CreateModelMixin):
    """批量新增城市组成员"""
    serializer_class = CityUserAddSerializer
    queryset = GroupUser.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (AdminPermission,)

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_CITY,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_CITY_ADD_USER_CODE) as log_context:
            log_context.log_vars = [request.data.get("city_id"), request.data.get("ids")]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

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

    def validate(self, request):
        err_msgs = []
        validated_data = {}
        city_id = self.request.data.get('city_id')
        ids = self.request.data.get('ids')
        if not City.objects.filter(id=city_id):
            err_msgs.append('City {} is not exist'.format(city_id))
        else:
            validated_data['city_id'] = city_id
        try:
            ids_list = [int(x) for x in ids.split('-')]
            match_queryset = CityUser.objects.filter(group_id=city_id, user_id__in=ids_list)
            if len(ids_list) != len(match_queryset):
                err_msgs.append('Improper parameter: ids')
            else:
                validated_data['ids_list'] = ids_list
        except ValueError:
            err_msgs.append('Invalid parameter: ids')
        if not err_msgs:
            return True, validated_data
        logger.error('[GroupUserDelView] Fail to validate when deleting groups members, the error messages are {}'.
                     format(','.join(err_msgs)))
        return False, None

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_CITY,
                           OperationLogType.OP_TYPE_DELETE,
                           OperationLogDesc.OP_DESC_CITY_REMOVE_USER_CODE) as log_context:
            log_context.log_vars = [request.data.get("city_id"), request.data.get("ids")]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        is_validated, validated_data = self.validate(request)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        city_id = validated_data.get('city_id')
        ids_list = validated_data.get('ids_list')
        CityUser.objects.filter(city_id=city_id, user_id__in=ids_list).delete()
        for user_id in ids_list:
            if not CityUser.objects.filter(user_id=user_id):
                GroupUser.objects.filter(group_id=1, user_id=int(user_id)).delete()
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 204, 'msg': '删除成功', 'access': access})


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


# ------------------------------activity view------------------------------
class ActivityCreateView(GenericAPIView, CreateModelMixin):
    """创建活动并申请发布"""
    serializer_class = ActivitySerializer
    queryset = Activity.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def validated(self, request):
        now_time = datetime.datetime.now()
        err_msgs = []
        data = self.request.data
        title = data.get('title')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        activity_category = data.get('activity_category')
        activity_type = data.get('activity_type')
        address = data.get('address')
        detail_address = data.get('detail_address')
        longitude = data.get('longitude')
        latitude = data.get('latitude')
        online_url = data.get('online_url')
        register_url = data.get('register_url')
        synopsis = data.get('synopsis')
        schedules = data.get('schedules')
        poster = data.get('post')
        try:
            if start_date <= datetime.datetime.strftime(now_time, '%Y-%m-%d'):
                err_msgs.append('The start date should be earlier than tomorrow')
            start_time = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end_time = datetime.datetime.strptime(end_date, '%Y-%m-%d')
            if (start_time - now_time).days > 60:
                err_msgs.append('The start time is at most 60 days later than the current time')
            if start_time >= end_time:
                err_msgs.append('The start time should not be later than the end time')
        except ValueError:
            err_msgs.append('Invalid datetime params')
        if not title:
            err_msgs.append('Activity title could not be empty')
        if activity_category not in range(1, 5):
            err_msgs.append('Invalid activity category: {}'.format(activity_category))
        if activity_type not in range(1, 4):
            err_msgs.append('Invalid activity type: {}'.format(activity_type))
        if not online_url.startswith('https://'):
            err_msgs.append('Invalid online url: {}'.format(online_url))
        if not register_url.startswith('https://'):
            err_msgs.append('Invalid register url: {}'.format(register_url))
        if poster not in range(1, 5):
            err_msgs.append('Invalid poster: {}'.format(poster))
        if err_msgs:
            logger.error('[ActivityCreateView] Fail to validate when creating activity, the error messages are {}'.
                         format(','.join(err_msgs)))
            return False, None
        validated_data = {
            'title': title,
            'start_date': start_date,
            'end_date': end_date,
            'activity_category': activity_category,
            'activity_type': activity_type,
            'address': address,
            'detail_address': detail_address,
            'longitude': longitude,
            'latitude': latitude,
            'online_url': online_url,
            'register_url': register_url,
            'synopsis': synopsis,
            'schedules': schedules,
            'poster': poster
        }
        return True, validated_data

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_CREATE,
                           OperationLogDesc.OP_DESC_ACTIVITY_CREATE_CODE) as log_context:
            log_context.log_vars = [request.data.get("title")]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        is_validated, data = self.validated(request)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        title = data.get('title')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        activity_category = data.get('activity_category')
        activity_type = data.get('activity_type')
        address = data.get('address')
        detail_address = data.get('detail_address')
        longitude = data.get('longitude')
        latitude = data.get('latitude')
        online_url = data.get('online_url')
        register_url = data.get('register_url')
        synopsis = data.get('synopsis')
        schedules = data.get('schedules')
        poster = data.get('post')
        user_id = self.request.user.id
        publish = self.request.GET.get('publish')

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
                register_method=2,
                online_url=online_url,
                register_url=register_url,
                synopsis=synopsis,
                schedules=json.dumps(schedules),
                poster=poster,
                status=2,
                user_id=user_id
            )
            access = refresh_access(self.request.user)
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
            register_method=2,
            online_url=online_url,
            register_url=register_url,
            synopsis=synopsis,
            schedules=json.dumps(schedules),
            poster=poster,
            user_id=user_id,
        )
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 201, 'msg': '活动草案创建成功！', 'access': access})


class ActivityUpdateView(GenericAPIView, UpdateModelMixin):
    """修改活动"""
    serializer_class = ActivityUpdateSerializer
    queryset = Activity.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_ACTIVITY_MODIFY_CODE) as log_context:
            log_context.log_vars = [kwargs.get("pk")]
            ret = self.update(request, *args, **kwargs)
            log_context.result = ret
            return ret

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

    def validate(self, request):
        err_msgs = []
        validated_data = {}
        activity_id = self.kwargs.get('pk')
        if not Activity.objects.filter(id=activity_id, status=2):
            err_msgs.append('Invalid activity id')
        else:
            validated_data['activity_id'] = activity_id
        if not err_msgs:
            return True, validated_data
        logger.error('[ApproveActivityView] Fail to validate when publishing activity, the error messages are {}'.
                     format(','.join(err_msgs)))
        return False, None

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_ACTIVITY_PUBLISH_PASS_CODE) as log_context:
            log_context.log_vars = [kwargs.get('pk')]
            ret = self.update(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def update(self, request, *args, **kwargs):
        is_validated, validated_data = self.validate(request)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        activity_id = validated_data.get('activity_id')
        logger.info('活动id: {}'.format(activity_id))
        img_url = gene_wx_code.run(activity_id)
        logger.info('生成活动页面二维码: {}'.format(img_url))
        Activity.objects.filter(id=activity_id, status=2).update(status=3, wx_code=img_url)
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 201, 'msg': '活动通过审核', 'access': access})


class DenyActivityView(GenericAPIView, UpdateModelMixin):
    """驳回申请"""
    queryset = Activity.objects.filter(is_delete=0, status=2)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def validate(self, request):
        err_msgs = []
        validated_data = {}
        activity_id = self.kwargs.get('pk')
        if not Activity.objects.filter(id=activity_id, status=2):
            err_msgs.append('Invalid activity id')
        else:
            validated_data['activity_id'] = activity_id
        if not err_msgs:
            return True, validated_data
        logger.error('[DenyActivityView] Fail to validate when rejecting activity, the error messages are {}'.
                     format(','.join(err_msgs)))
        return False, None

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_ACTIVITY_PUBLISH_REJECT_CODE) as log_context:
            log_context.log_vars = [kwargs.get("pk")]
            ret = self.update(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def update(self, request, *args, **kwargs):
        is_validated, validated_data = self.validate(request)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        activity_id = validated_data.get('activity_id')
        Activity.objects.filter(id=activity_id, status=2).update(status=1)
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 201, 'msg': '活动申请已驳回', 'access': access})


class ActivityDeleteView(GenericAPIView, UpdateModelMixin):
    """删除活动"""
    queryset = Activity.objects.filter(is_delete=0, status__gt=2)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def validate(self, request):
        err_msgs = []
        validated_data = {}
        activity_id = self.kwargs.get('pk')
        if not Activity.objects.filter(id=activity_id, status__gt=2, is_delete=0):
            err_msgs.append('Invalid activity id: {}'.format(activity_id))
        else:
            validated_data['activity_id'] = activity_id
        if not err_msgs:
            return True, validated_data
        logger.error('[ActivityDeleteView] Fail to validate when deleting activity, the error messages are {}'.
                     format(','.join(err_msgs)))
        return False, None

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_DELETE,
                           OperationLogDesc.OP_DESC_ACTIVITY_DELETE_CODE) as log_context:
            log_context.log_vars = [kwargs.get("pk")]
            ret = self.update(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def update(self, request, *args, **kwargs):
        is_validated, validated_data = self.validate(request)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        activity_id = validated_data.get('activity_id')
        Activity.objects.filter(id=activity_id).update(is_delete=1)
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 204, 'msg': '成功删除活动', 'access': access})


class DraftUpdateView(GenericAPIView, UpdateModelMixin):
    """修改活动草案"""
    serializer_class = ActivityDraftUpdateSerializer
    queryset = Activity.objects.filter(is_delete=0, status=1)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def validated(self, request):
        now_time = datetime.datetime.now()
        err_msgs = []
        data = self.request.data
        activity_id = self.kwargs.get('pk')
        title = data.get('title')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        activity_category = data.get('activity_category')
        activity_type = data.get('activity_type')
        address = data.get('address')
        detail_address = data.get('detail_address')
        longitude = data.get('longitude')
        latitude = data.get('latitude')
        online_url = data.get('online_url')
        register_url = data.get('register_url')
        synopsis = data.get('synopsis')
        schedules = data.get('schedules')
        poster = data.get('post')
        if Activity.objects.filter(id=activity_id, user_id=self.request.user.id, status=1):
            err_msgs.append('Invalid activity id: {}'.format(activity_id))
        try:
            if start_date <= datetime.datetime.strftime(now_time, '%Y-%m-%d'):
                err_msgs.append('The start date should be earlier than tomorrow')
            start_time = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end_time = datetime.datetime.strptime(end_date, '%Y-%m-%d')
            if (start_time - now_time).days > 60:
                err_msgs.append('The start time is at most 60 days later than the current time')
            if start_time >= end_time:
                err_msgs.append('The start time should not be later than the end time')
        except ValueError:
            err_msgs.append('Invalid datetime params')
        if not title:
            err_msgs.append('Activity title could not be empty')
        if activity_category not in range(1, 5):
            err_msgs.append('Invalid activity category: {}'.format(activity_category))
        if activity_type not in range(1, 4):
            err_msgs.append('Invalid activity type: {}'.format(activity_type))
        if not online_url.startswith('https://'):
            err_msgs.append('Invalid online url: {}'.format(online_url))
        if not register_url.startswith('https://'):
            err_msgs.append('Invalid register url: {}'.format(register_url))
        if poster not in range(1, 5):
            err_msgs.append('Invalid poster: {}'.format(poster))
        if err_msgs:
            logger.error('[ActivityCreateView] Fail to validate when creating activity, the error messages are {}'.
                         format(','.join(err_msgs)))
            return False, None
        validated_data = {
            'activity_id': activity_id,
            'title': title,
            'start_date': start_date,
            'end_date': end_date,
            'activity_category': activity_category,
            'activity_type': activity_type,
            'address': address,
            'detail_address': detail_address,
            'longitude': longitude,
            'latitude': latitude,
            'online_url': online_url,
            'register_url': register_url,
            'synopsis': synopsis,
            'schedules': schedules,
            'poster': poster
        }
        return True, validated_data

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_ACTIVITY_MODIFY_DRAFT_CODE) as log_context:
            log_context.log_vars = [kwargs.get('pk')]
            ret = self.update(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def update(self, request, *args, **kwargs):
        is_validated, data = self.validated(request)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        activity_id = data.get('activity_id')
        title = data.get('title')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        activity_category = data.get('activity_category')
        activity_type = data.get('activity_type')
        address = data.get('address')
        detail_address = data.get('detail_address')
        longitude = data.get('longitude')
        latitude = data.get('latitude')
        online_url = data.get('online_url')
        register_url = data.get('register_url')
        synopsis = data.get('synopsis')
        schedules = data.get('schedules')
        poster = data.get('post')
        user_id = self.request.user.id
        publish = self.request.GET.get('publish')

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
                register_method=2,
                online_url=online_url,
                register_url=register_url,
                synopsis=synopsis,
                schedules=json.dumps(schedules),
                poster=poster,
                status=2
            )
            access = refresh_access(self.request.user)
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
            register_method=2,
            online_url=online_url,
            register_url=register_url,
            synopsis=synopsis,
            schedules=json.dumps(schedules),
            poster=poster,
        )
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 201, 'msg': '修改并保存活动草案', 'access': access})


class DraftView(GenericAPIView, RetrieveModelMixin, DestroyModelMixin):
    """查询、删除活动草案"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_DELETE,
                           OperationLogDesc.OP_DESC_ACTIVITY_DELETE_DRAFT_CODE) as log_context:
            log_context.log_vars = [kwargs.get("pk")]
            ret = self.destroy(request, *args, **kwargs)
            log_context.result = ret
            return ret

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
        self.queryset = self.queryset.filter(status__gt=2, start_date__gte=datetime.datetime.now().
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

    def validate(self, request):
        err_msgs = []
        activity_id = self.request.data.get('activity')
        if not isinstance(activity_id, int):
            err_msgs.append('Invalid activity id: {}'.format(activity_id))
        if not Activity.objects.filter(id=activity_id, status__in=[3, 4, 5], is_delete=0):
            err_msgs.append('Activity {} is not exist'.format(activity_id))
        if err_msgs:
            logger.error('[ActivityCollectView] Fail to validate when collect activity, the error messages are {}'.
                         format(','.join(err_msgs)))
            return False
        return True

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_COLLECT,
                           OperationLogDesc.OP_DESC_ACTIVITY_COLLECT_CODE) as log_context:
            log_context.log_vars = [request.data.get('activity')]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        if not self.validate(request):
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        user_id = self.request.user.id
        activity_id = self.request.data.get('activity')
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

    def validate(self, request):
        err_msgs = []
        if not Activity.objects.filter(id=self.kwargs.get('pk'), is_delete=0):
            err_msgs.append('Activity {} is not exist'.format(self.kwargs.get('pk')))
        if not ActivityCollect.objects.filter(activity_id=self.kwargs.get('pk'), user_id=self.request.user.id):
            err_msgs.append('User {} had not collected activity {}'.format(self.request.user.id, self.kwargs.get('pk')))
        if not err_msgs:
            return True
        logger.error('[ActivityCollectDelView] Fail to validate when deleting meeting collection, the error messages'
                     'are {}'.format(','.join(err_msgs)))
        return False

    def delete(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_CANCEL_COLLECT,
                           OperationLogDesc.OP_DESC_ACTIVITY_CANCEL_COLLECT_CODE) as log_context:
            log_context.log_vars = [kwargs.get('pk')]
            ret = self.destroy(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def destroy(self, request, *args, **kwargs):
        if not self.validate(request):
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
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
        res = {'collected_meetings_count': collected_meetings_count,
               'collected_activities_count': collected_activities_count}
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
            res['drafts_count'] = drafts_count
            res['publishing_activities_count'] = publishing_activities_count
        if activity_level == 3:
            published_activities_count = len(Activity.objects.filter(is_delete=0, status__gt=2).values())
            drafts_count = len(Activity.objects.filter(is_delete=0, status=1, user_id=user_id).values())
            publishing_activities_count = len(Activity.objects.filter(is_delete=0, status=2).values())
            res['published_activities_count'] = published_activities_count
            res['drafts_count'] = drafts_count
            res['publishing_activities_count'] = publishing_activities_count
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
