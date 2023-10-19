import datetime
import logging
import json
import secrets
import time
from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from rest_framework import status
from rest_framework.filters import SearchFilter
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin, DestroyModelMixin, \
    UpdateModelMixin
from openeuler.models import User, Group, Meeting, GroupUser, Collect, Video, Record, \
    Activity, ActivityCollect
from openeuler.permissions import MaintainerPermission, AdminPermission, \
    ActivityAdminPermission, SponsorPermission, QueryPermission
from openeuler.serializers import LoginSerializer, GroupsSerializer, MeetingSerializer, \
    UsersSerializer, UserSerializer, GroupUserAddSerializer, GroupSerializer, UsersInGroupSerializer, \
    UserGroupSerializer, MeetingListSerializer, GroupUserDelSerializer, UserInfoSerializer, SigsSerializer, \
    MeetingsDataSerializer, AllMeetingsSerializer, CollectSerializer, SponsorSerializer, SponsorInfoSerializer, \
    ActivitySerializer, ActivitiesSerializer, ActivityDraftUpdateSerializer, ActivityUpdateSerializer, \
    ActivityCollectSerializer, ActivityRetrieveSerializer
from rest_framework.response import Response
from multiprocessing import Process
from openeuler.send_email import sendmail
from rest_framework import permissions
from openeuler.utils import gene_wx_code, drivers, send_cancel_email
from rest_framework_simplejwt.tokens import RefreshToken
from app_meeting_server.utils.auth import CustomAuthentication
from app_meeting_server.utils import wx_apis, crypto_gcm
from app_meeting_server.utils.operation_log import LoggerContext, OperationLogModule, OperationLogDesc, OperationLogType, OperationLogResult
from app_meeting_server.utils.common import get_cur_date

logger = logging.getLogger('log')
offline = 1
online = 2


def refresh_access(user):
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    encrypt_access = crypto_gcm.aes_gcm_encrypt(access, settings.AES_GCM_SECRET, settings.AES_GCM_IV)
    User.objects.filter(id=user.id).update(signature=encrypt_access)
    return encrypt_access


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
        if User.objects.get(id=self.request.user.id).agree_privacy_policy:
            resp = JsonResponse({
                'code': 400,
                'msg': 'The user has signed privacy policy agreement already.'
            })
            return resp
        User.objects.filter(id=self.request.user.id).update(agree_privacy_policy=True,
                                                            agree_privacy_policy_time=now_time,
                                                            agree_privacy_policy_version=settings.PRIVACY_POLICY_VERSION)
        access = refresh_access(self.request.user)
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
        User.objects.filter(id=self.request.user.id).update(revoke_agreement_time=now_time)
        refresh_access(self.request.user)
        resp = JsonResponse({
            'code': 201,
            'msg': 'Revoke agreement of privacy policy'
        })
        return resp


class GroupsView(GenericAPIView, ListModelMixin):
    """查询所有SIG组的名称"""
    serializer_class = GroupsSerializer
    queryset = Group.objects.all().order_by('group_name')
    filter_backends = [SearchFilter]
    search_fields = ['group_name']

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class SigsView(GenericAPIView, ListModelMixin):
    """查询所有SIG组的名称、首页、邮件列表、IRC频道及成员的nickname、gitee_name、avatar"""
    serializer_class = SigsSerializer
    queryset = Group.objects.all()

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class GroupView(GenericAPIView, RetrieveModelMixin):
    """查询单个SIG组"""
    serializer_class = GroupSerializer
    queryset = Group.objects.all()

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class UsersIncludeView(GenericAPIView, ListModelMixin):
    """查询所选SIG组的所有成员"""
    serializer_class = UsersInGroupSerializer
    queryset = User.objects.all()
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (CustomAuthentication,)
    permission_classes = (AdminPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        try:
            groupusers = GroupUser.objects.filter(group_id=self.kwargs['pk']).all()
            ids = [x.user_id for x in groupusers]
            user = User.objects.filter(id__in=ids, is_delete=0)
            return user
        except KeyError:
            pass


class UsersExcludeView(GenericAPIView, ListModelMixin):
    """查询不在该组的所有成员"""
    serializer_class = UsersSerializer
    queryset = User.objects.all().order_by('nickname')
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (CustomAuthentication,)
    permission_classes = (AdminPermission,)

    def get(self, request, *args, **kwargs):
        if not Group.objects.filter(id=self.kwargs.get('pk')):
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        groupusers = GroupUser.objects.filter(group_id=self.kwargs['pk']).all()
        ids = [x.user_id for x in groupusers]
        user = User.objects.filter().exclude(id__in=ids)
        return user


class UserGroupView(GenericAPIView, ListModelMixin):
    """查询该用户的SIG组以及该组的etherpad"""
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


class UserView(GenericAPIView, UpdateModelMixin):
    """更新用户gitee_name"""
    serializer_class = UserSerializer
    queryset = User.objects.all()
    authentication_classes = (CustomAuthentication,)
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


class GroupUserAddView(GenericAPIView, CreateModelMixin):
    """SIG组批量新增成员"""
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


class UserInfoView(GenericAPIView, RetrieveModelMixin):
    """查询本机用户的level和gitee_name"""
    serializer_class = UserInfoSerializer
    queryset = User.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)

    def get(self, request, *args, **kwargs):
        user_id = kwargs.get('pk')
        if user_id != request.user.id:
            logger.warning('user_id did not match.')
            logger.warning('user_id:{}, request.user.id:{}'.format(user_id, request.user.id))
            return JsonResponse({"code": 400, "message": "错误操作，信息不匹配！"})
        return self.retrieve(request, *args, **kwargs)


class SponsorsView(GenericAPIView, ListModelMixin):
    """活动发起人列表"""
    serializer_class = SponsorSerializer
    queryset = User.objects.filter(activity_level=2, is_delete=0)
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class NonSponsorView(GenericAPIView, ListModelMixin):
    """非活动发起人列表"""
    serializer_class = SponsorSerializer
    queryset = User.objects.filter(activity_level=1, is_delete=0)
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class SponsorAddView(GenericAPIView, CreateModelMixin):
    """批量添加活动发起人"""
    queryset = User.objects.all()
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
        logger.error('[SponsorAddView] Fail to validate when adding activity sponsors, the error messages are {}'.
                     format(','.join(err_msgs)))
        return False, None

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_USER_ADD_ACTIVITY_SPONSOR_CODE) as log_context:
            log_context.log_vars = [request.data.get('ids')]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        is_validated, validated_data = self.validate(request)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        ids_list = validated_data.get('ids_list')
        User.objects.filter(id__in=ids_list, activity_level=1, is_delete=0).update(activity_level=2)
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 201, 'msg': '添加成功', 'access': access})


class SponsorDelView(GenericAPIView, CreateModelMixin):
    """批量删除组成员"""
    queryset = GroupUser.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def validate(self, request):
        err_msgs = []
        validated_data = {}
        ids = self.request.data.get('ids')
        try:
            ids_list = [int(x) for x in ids.split('-')]
            match_queryset = User.objects.filter(id__in=ids_list, activity_level=2)
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
        User.objects.filter(id__in=ids_list, activity_level=2, is_delete=0).update(activity_level=1)
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 204, 'msg': '删除成功', 'access': access})


class SponsorInfoView(GenericAPIView, UpdateModelMixin):
    """修改活动发起人信息"""
    serializer_class = SponsorInfoSerializer
    queryset = User.objects.filter(is_delete=0, activity_level=2)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_USER_MODIIFY_CODE) as log_context:
            log_context.log_vars = [kwargs.get("pk"), request.data.get("gitee_name")]
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


# ------------------------------meeting view------------------------------
class MeetingsWeeklyView(GenericAPIView, ListModelMixin):
    """查询前后一周的所有会议"""
    serializer_class = MeetingListSerializer
    queryset = Meeting.objects.filter(is_delete=0)
    filter_backends = [SearchFilter]
    search_fields = ['topic', 'group_name']

    def get(self, request, *args, **kwargs):
        self.queryset = self.queryset.filter((Q(
            date__gte=str(datetime.datetime.now() - datetime.timedelta(days=7))[:10]) & Q(
            date__lte=str(datetime.datetime.now() + datetime.timedelta(days=7))[:10]))).order_by('-date', 'start')
        return self.list(request, *args, **kwargs)


class MeetingsDailyView(GenericAPIView, ListModelMixin):
    """查询本日的所有会议"""
    serializer_class = MeetingListSerializer
    queryset = Meeting.objects.filter(is_delete=0)

    def get(self, request, *args, **kwargs):
        self.queryset = self.queryset.filter(date=str(datetime.datetime.now())[:10]).order_by('start')
        return self.list(request, *args, **kwargs)


class MeetingsRecentlyView(GenericAPIView, ListModelMixin):
    """查询最近的会议"""
    serializer_class = MeetingListSerializer
    queryset = Meeting.objects.filter(is_delete=0)

    def get(self, request, *args, **kwargs):
        self.queryset = self.queryset.filter(date__gte=datetime.datetime.now().strftime('%Y-%m-%d')). \
            order_by('date', 'start')
        return self.list(request, *args, **kwargs)


class MeetingView(GenericAPIView, RetrieveModelMixin):
    """查询会议(id)"""
    serializer_class = MeetingListSerializer
    queryset = Meeting.objects.filter(is_delete=0)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class MeetingDelView(GenericAPIView, DestroyModelMixin):
    """删除会议(mid)"""
    serializer_class = MeetingSerializer
    queryset = Meeting.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MaintainerPermission,)

    def validate(self, request):
        err_msgs = []
        validated_data = {}
        mid = self.kwargs.get('mid')
        if not Meeting.objects.filter(mid=mid, is_delete=0):
            err_msgs.append('Invalid meeting id: {}'.format(mid))
        elif not (Meeting.objects.filter(mid=mid, user_id=self.request.user.id) or
                  User.objects.filter(id=self.request.user.id, level=3)):
            err_msgs.append('User {} has no access to delete meeting {}'.format(self.request.user.id, mid))
        else:
            validated_data['mid'] = mid
        if not err_msgs:
            return True, validated_data
        logger.error('[MeetingDelView] Fail to validate when deleting meetings, the error messages are {}'.format(
            ','.join(err_msgs)))
        return False, None

    def delete(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_MEETING,
                           OperationLogType.OP_TYPE_DELETE,
                           OperationLogDesc.OP_DESC_MEETING_DELETE_CODE) as log_context:
            log_context.log_vars = [kwargs.get('mid')]
            ret = self.destroy(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def destroy(self, request, *args, **kwargs):
        is_validated, validated_data = self.validate(request)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        mid = validated_data.get('mid')

        drivers.cancelMeeting(mid)

        # 会议作软删除
        meeting = Meeting.objects.get(mid=mid)
        Meeting.objects.filter(mid=mid).update(is_delete=1)
        meeting_id = meeting.id
        mid = meeting.mid
        logger.info('{} has canceled the meeting which mid was {}'.format(request.user.gitee_name, mid))

        # 发送删除通知邮件
        send_cancel_email.sendmail(mid)

        # 发送会议取消通知
        collections = Collect.objects.filter(meeting_id=meeting_id)
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
                encrypt_openid = user.openid
                openid = crypto_gcm.aes_gcm_decrypt(encrypt_openid, settings.AES_GCM_SECRET)
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
        access = refresh_access(self.request.user)
        return JsonResponse({"code": 204, "message": "Delete successfully.", "access": access})


class MeetingsDataView(GenericAPIView, ListModelMixin):
    """网页日历数据"""
    serializer_class = MeetingsDataSerializer
    queryset = Meeting.objects.filter(is_delete=0).order_by('start')

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).filter(
            date__gte=(datetime.datetime.now() - datetime.timedelta(days=180)).strftime('%Y-%m-%d'),
            date__lte=(datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')).values()
        tableData = []
        date_list = []
        for query in queryset:
            date_list.append(query.get('date'))
        date_list = sorted(list(set(date_list)))
        records = Record.objects.all().values()
        record_dict = {}
        for record in records:
            if record['platform'] == 'bilibili' and record['url']:
                record_dict[record['mid']] = record['url']
        for date in date_list:
            timeData = []
            for meeting in queryset:
                if meeting['date'] != date:
                    continue
                timeData.append({
                    'id': meeting['id'],
                    'group_name': meeting['group_name'],
                    'startTime': meeting['start'],
                    'endTime': meeting['end'],
                    'duration_time': meeting['start'] + '-' + meeting['end'],
                    'name': meeting['topic'],
                    'creator': meeting['sponsor'],
                    'detail': meeting['agenda'],
                    'join_url': meeting['join_url'],
                    'meeting_id': meeting['mid'],
                    'etherpad': meeting['etherpad'],
                    'platform': meeting['mplatform'],
                    'video_url': record_dict.get(meeting['mid'], '')
                })
            tableData.append({
                'date': date,
                'timeData': timeData
            })
        return Response({'tableData': tableData})


class SigMeetingsDataView(GenericAPIView, ListModelMixin):
    """网页SIG组日历数据"""
    serializer_class = MeetingsDataSerializer
    queryset = Meeting.objects.filter(is_delete=0).order_by('date', 'start')

    def get(self, request, *args, **kwargs):
        group_name = kwargs.get('gn')
        queryset = self.filter_queryset(self.get_queryset()).filter(group_name=group_name).filter((Q(
            date__gte=str(datetime.datetime.now() - datetime.timedelta(days=180))[:10]) & Q(
            date__lte=str(datetime.datetime.now() + datetime.timedelta(days=30))[:10]))).values()
        tableData = []
        date_list = []
        for query in queryset:
            date_list.append(query.get('date'))
        date_list = sorted(list(set(date_list)))
        records = Record.objects.all().values()
        record_dict = {}
        for record in records:
            if record['platform'] == 'bilibili' and record['url']:
                record_dict[record['mid']] = record['url']
        for date in date_list:
            timeData = []
            for meeting in queryset:
                if meeting['date'] != date:
                    continue
                timeData.append({
                    'id': meeting['id'],
                    'group_name': meeting['group_name'],
                    'startTime': meeting['start'],
                    'endTime': meeting['end'],
                    'duration_time': meeting['start'] + '-' + meeting['end'],
                    'name': meeting['topic'],
                    'creator': meeting['sponsor'],
                    'detail': meeting['agenda'],
                    'join_url': meeting['join_url'],
                    'meeting_id': meeting['mid'],
                    'etherpad': meeting['etherpad'],
                    'platform': meeting['mplatform'],
                    'video_url': record_dict.get(meeting['mid'], '')
                })
            tableData.append({
                'date': date,
                'timeData': timeData
            })
        return Response({'tableData': tableData})


class MeetingsView(GenericAPIView, CreateModelMixin):
    """创建会议"""
    serializer_class = MeetingSerializer
    queryset = Meeting.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MaintainerPermission,)

    def validate(self, request):
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
        community = data.get('community', 'openeuler')
        emaillist = data.get('emaillist')
        summary = data.get('agenda')
        record = data.get('record')
        etherpad = data.get('etherpad')
        if not isinstance(platform, str):
            err_msgs.append('Field platform must be string type')
        else:
            host_dict = settings.MEETING_HOSTS.get(platform.lower())
            if not host_dict or not isinstance(host_dict, dict):
                err_msgs.append('Could not match any meeting host')
        try:
            start_time = datetime.datetime.strptime(' '.join([date, start]), '%Y-%m-%d %H:%M')
            end_time = datetime.datetime.strptime(' '.join([date, end]), '%Y-%m-%d %H:%M')
            if start_time <= now_time:
                err_msgs.append('The start time should not be later than the current time')
            if (start_time - now_time).days > 60:
                err_msgs.append('The start time is at most 60 days later than the current time')
            if start_time >= end_time:
                err_msgs.append('The start time should not be later than the end time')
        except ValueError:
            err_msgs.append('Invalid start time or end time')
        if not Group.objects.filter(group_name=group_name):
            err_msgs.append('Invalid group name: {}'.format(group_name))
        if not etherpad.startswith(settings.ETHERPAD_PREFIX):
            err_msgs.append('Invalid etherpad address')
        if community != settings.COMMUNITY.lower():
            err_msgs.append('The field community must be the same as configure')
        # todo 1.emaillist这里直接取，还是判断参数错误？  2.没有判断的参数有：sponsor, summary, record
        if len(emaillist) > 100:
            emaillist = emaillist[:100]
        if err_msgs:
            logger.error('[MeetingsView] Fail to validate when creating meetings, the error messages are {}'.format(
                ','.join(err_msgs)))
            return False, None
        validated_data = {
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
        t1 = time.time()
        # 获取data
        is_validated, data = self.validate(request)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        platform = data.get('platform')
        host_dict = data.get('host_dict')
        date = data.get('date')
        start = data.get('start')
        end = data.get('end')
        topic = data.get('topic')
        sponsor = data.get('sponsor')
        group_name = data.get('group_name')
        community = data.get('community')
        emaillist = data.get('emaillist')
        summary = data.get('agenda')
        user_id = data.get('user_id')
        group_id = data.get('group_id')
        record = data.get('record')
        etherpad = data.get('etherpad')
        start_search = datetime.datetime.strftime(
            (datetime.datetime.strptime(start, '%H:%M') - datetime.timedelta(minutes=30)),
            '%H:%M')
        end_search = datetime.datetime.strftime(
            (datetime.datetime.strptime(end, '%H:%M') + datetime.timedelta(minutes=30)),
            '%H:%M')
        # 查询待创建的会议与现有的预定会议是否冲突
        host_ids = list(host_dict.keys())
        meetings = Meeting.objects.filter(is_delete=0, date=date, end__gt=start_search, start__lt=end_search,
                                          mplatform=platform).values()
        unavailable_host_ids = [meeting['host_id'] for meeting in meetings]
        available_host_id = list(set(host_ids) - set(unavailable_host_ids))
        logger.info('avilable_host_id:{}'.format(available_host_id))
        if len(available_host_id) == 0:
            logger.warning('{}暂无可用host'.format(platform))
            return JsonResponse({'code': 1000, 'message': '暂无可用host,请前往官网查看预定会议'})
        # 从available_host_id中随机生成一个host_id,并在host_dict中取出
        host_id = secrets.choice(available_host_id)
        host = host_dict[host_id]
        logger.info('host_id:{}'.format(host_id))
        logger.info('host:{}'.format(host))

        status, content = drivers.createMeeting(platform, date, start, end, topic, host, record)
        if status not in [200, 201]:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        mid = content['mid']
        start_url = content.get('start_url')
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
        logger.info('{} has created a {} meeting which mid is {}.'.format(sponsor, platform, mid))
        logger.info('meeting info: {},{}-{},{}'.format(date, start, end, topic))

        # 发送email
        m = {
            'mid': mid,
            'topic': topic,
            'date': date,
            'start': start,
            'end': end,
            'join_url': join_url,
            'sig_name': group_name,
            'emaillist': emaillist,
            'platform': platform,
            'etherpad': etherpad,
            'agenda': summary
        }
        p1 = Process(target=sendmail, args=(m, record))
        p1.start()

        # 如果开启录制功能，则在Video表中创建一条数据
        if record == 'cloud':
            Video.objects.create(
                mid=mid,
                topic=data['topic'],
                community=community,
                group_name=data['group_name'],
                agenda=data['agenda'] if 'agenda' in data else ''
            )
            logger.info('meeting {} was created with auto recording.'.format(mid))

        # 返回请求数据
        access = refresh_access(self.request.user)
        resp = {'code': 201, 'message': '创建成功', 'access': access}
        meeting = Meeting.objects.get(mid=mid)
        resp['id'] = meeting.id
        t3 = time.time()
        print('total waste: {}'.format(t3 - t1))
        return JsonResponse(resp)


class MyMeetingsView(GenericAPIView, ListModelMixin):
    """查询我创建的所有会议"""
    serializer_class = MeetingListSerializer
    queryset = Meeting.objects.all().filter(is_delete=0)
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        user_id = self.request.user.id
        queryset = Meeting.objects.filter(is_delete=0, user_id=user_id).order_by('-date', 'start')
        if User.objects.get(id=user_id).level == 3:
            queryset = Meeting.objects.filter(is_delete=0).order_by('-date', 'start')
        return queryset


class AllMeetingsView(GenericAPIView, ListModelMixin):
    """列出所有会议"""
    serializer_class = AllMeetingsSerializer
    queryset = Meeting.objects.all()
    filter_backends = [SearchFilter]
    search_fields = ['is_delete', 'group_name', 'sponsor', 'date', 'start', 'end']
    permission_classes = (QueryPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class CollectView(GenericAPIView, ListModelMixin, CreateModelMixin):
    """收藏会议"""
    serializer_class = CollectSerializer
    queryset = Collect.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)

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
        logger.error('[CollectView] Fail to validate when creating meetings, the error messages are {}'.format(
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
        meeting_id = validated_data.get('meeting_id')
        Collect.objects.create(meeting_id=meeting_id, user_id=user_id)
        collection_id = Collect.objects.get(meeting_id=meeting_id, user_id=user_id).id
        access = refresh_access(self.request.user)
        resp = {'code': 201, 'msg': 'collect successfully', 'collection_id': collection_id, 'access': access}
        return JsonResponse(resp)

    def get_queryset(self):
        queryset = Collect.objects.filter(user_id=self.request.user.id)
        return queryset


class CollectDelView(GenericAPIView, DestroyModelMixin):
    """取消收藏"""
    serializer_class = CollectSerializer
    queryset = Collect.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)

    def validate(self, request):
        err_msgs = []
        if not Meeting.objects.filter(id=self.kwargs.get('pk'), is_delete=0):
            err_msgs.append('Meeting {} is not exist'.format(self.kwargs.get('pk')))
        if not Collect.objects.filter(meeting_id=self.kwargs.get('pk'), user_id=self.request.user.id):
            err_msgs.append('User {} had not collected meeting {}'.format(self.request.user.id, self.kwargs.get('pk')))
        if not err_msgs:
            return True
        logger.error('[CollectDelView] Fail to validate when deleting meeting collection, the error messages are {}'.
                     format(','.join(err_msgs)))
        return False

    def delete(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_MEETING,
                           OperationLogType.OP_TYPE_CANCEL_COLLECT,
                           OperationLogDesc.OP_DESC_MEETING_CANCEL_COLLECT_CODE) as log_context:
            log_context.log_vars = [kwargs.get("pk")]
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


class MyCollectionsView(GenericAPIView, ListModelMixin):
    """我收藏的会议(列表)"""
    serializer_class = MeetingListSerializer
    queryset = Meeting.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        user_id = self.request.user.id
        collection_lst = Collect.objects.filter(user_id=user_id).values_list('meeting', flat=True)
        queryset = Meeting.objects.filter(is_delete=0, id__in=collection_lst).order_by('-date', 'start')
        return queryset


class ParticipantsView(GenericAPIView, RetrieveModelMixin):
    """查询会议的参会者"""
    permission_classes = (QueryPermission,)

    def get(self, request, *args, **kwargs):
        mid = kwargs.get('mid')
        if mid not in Meeting.objects.filter(is_delete=0).values_list('mid', flat=True):
            return JsonResponse({
                'code': 400,
                'msg': 'Meeting {} does not exist'.format(mid)
            })
        status, res = drivers.getParticipants(mid)
        if status == 200:
            return JsonResponse(res)
        else:
            resp = JsonResponse(res)
            resp.status_code = 400
            return resp


# ------------------------------activity view------------------------------
class DraftsView(GenericAPIView, ListModelMixin):
    """审核列表"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.filter(is_delete=0, status=2)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class DraftView(GenericAPIView, RetrieveModelMixin):
    """待发布详情"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.filter(is_delete=0, status=2)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class ActivityView(GenericAPIView, CreateModelMixin):
    """创建活动并申请发布"""
    serializer_class = ActivitySerializer
    queryset = Activity.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def validate(self, request):
        now_time = datetime.datetime.now()
        err_msgs = []
        data = self.request.data
        title = data.get('title')
        date = data.get('date')
        activity_type = data.get('activity_type')
        synopsis = data.get('synopsis')
        poster = data.get('poster')
        register_url = data.get('register_url')
        address = data.get('address')
        detail_address = data.get('detail_address')
        longitude = data.get('longitude')
        latitude = data.get('latitude')
        start = data.get('start')
        end = data.get('end')
        schedules = data.get('schedules')
        try:
            if date <= datetime.datetime.strftime(now_time, '%Y-%m-%d'):
                err_msgs.append('The start date should be earlier than tomorrow')
            start_time = datetime.datetime.strptime(' '.join([date, start]), '%Y-%m-%d %H:%M')
            end_time = datetime.datetime.strptime(' '.join([date, end]), '%Y-%m-%d %H:%M')
            # todo 1.没有校验的参数有：synopsis， address, detail_address, longitude, latitude, schedules
            if start_time <= now_time:
                err_msgs.append('The start time should not be later than the current time')
            if (start_time - now_time).days > 60:
                err_msgs.append('The start time is at most 60 days later than the current time')
            if start_time >= end_time:
                err_msgs.append('The start time should not be later than the end time')
        except ValueError:
            err_msgs.append('Invalid datetime params')
        if not title:
            err_msgs.append('Activity title could not be empty')
        if activity_type not in [offline, online]:
            err_msgs.append('Invalid activity type: {}'.format(activity_type))
        if poster not in range(1, 5):
            err_msgs.append('Invalid poster: {}'.format(poster))
        if not register_url.startswith('https://'):
            err_msgs.append('Invalid register url: {}'.format(register_url))
        if err_msgs:
            logger.error('[ActivityView] Fail to validate when creating activity, the error messages are {}'.format(
                ','.join(err_msgs)))
            return False, None
        validated_data = {
            'title': title,
            'date': date,
            'activity_type': activity_type,
            'synopsis': synopsis,
            'poster': poster,
            'register_url': register_url,
            'address': address,
            'detail_address': detail_address,
            'longitude': longitude,
            'latitude': latitude,
            'start': start,
            'end': end,
            'schedules': schedules
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
        is_validated, data = self.validate(request)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        title = data.get('title')
        date = data.get('date')
        activity_type = data.get('activity_type')
        synopsis = data.get('synopsis')
        poster = data.get('poster')
        register_url = data.get('register_url')
        user_id = self.request.user.id
        # 线下活动
        if activity_type == offline:
            address = data.get('address')
            detail_address = data.get('detail_address')
            longitude = data.get('longitude')
            latitude = data.get('latitude')
            Activity.objects.create(
                title=title,
                date=date,
                activity_type=activity_type,
                synopsis=synopsis,
                address=address,
                detail_address=detail_address,
                longitude=longitude,
                latitude=latitude,
                schedules=json.dumps(data.get('schedules')),
                poster=poster,
                user_id=user_id,
                status=2,
                register_url=register_url
            )
        # 线上活动
        if activity_type == online:
            start = data.get('start')
            end = data.get('end')
            Activity.objects.create(
                title=title,
                date=date,
                start=start,
                end=end,
                activity_type=activity_type,
                synopsis=synopsis,
                schedules=json.dumps(data.get('schedules')),
                poster=poster,
                user_id=user_id,
                status=2,
                register_url=register_url
            )
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 201, 'msg': '活动申请发布成功！', 'access': access})


class ActivitiesView(GenericAPIView, ListModelMixin):
    """活动列表"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.filter(is_delete=0, status__gt=2).order_by('-date', 'id')
    filter_backends = [SearchFilter]
    search_fields = ['title']

    def get(self, request, *args, **kwargs):
        activity_status = self.request.GET.get('activity')
        activity_type = self.request.GET.get('activity_type')
        if activity_status == 'registering':
            self.queryset = self.queryset.filter(status__in=[3, 4])
        if activity_status == 'going':
            self.queryset = self.queryset.filter(status=4)
        if activity_status == 'completed':
            self.queryset = self.queryset.filter(status=5)
        if activity_type:
            try:
                if int(activity_type) == 1:
                    self.queryset = self.queryset.filter(activity_type=1)
                if int(activity_type) == 2:
                    self.queryset = self.queryset.filter(activity_type=2)
                if int(activity_type) == 1 and activity_status == 'registering':
                    self.queryset = self.queryset.filter(activity_type=1, status__in=[3, 4])
                if int(activity_type) == 1 and activity_status == 'going':
                    self.queryset = self.queryset.filter(activity_type=1, status=4)
                if int(activity_type) == 1 and activity_status == 'completed':
                    self.queryset = self.queryset.filter(activity_type=1, status=5)
                if int(activity_type) == 2 and activity_status == 'registering':
                    self.queryset = self.queryset.filter(activity_type=2, status__in=[3, 4])
                if int(activity_type) == 2 and activity_status == 'going':
                    self.queryset = self.queryset.filter(activity_type=2, status=4)
                if int(activity_type) == 2 and activity_status == 'completed':
                    self.queryset = self.queryset.filter(activity_type=2, status=5)
            except TypeError:
                pass
        return self.list(request, *args, **kwargs)


class RecentActivitiesView(GenericAPIView, ListModelMixin):
    """最近的活动列表"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.filter(is_delete=0)

    def get(self, request, *args, **kwargs):
        self.queryset = self.queryset.filter(status__gt=2, date__gt=datetime.datetime.now().strftime('%Y-%m-%d')). \
            order_by('-date', 'id')
        return self.list(request, *args, **kwargs)


class SponsorActivitiesView(GenericAPIView, ListModelMixin):
    """活动发起人的活动列表"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Activity.objects.filter(is_delete=0, status__gt=2, user_id=self.request.user.id)
        return queryset


class ActivityRetrieveView(GenericAPIView, RetrieveModelMixin):
    """查询单个活动"""
    serializer_class = ActivityRetrieveSerializer
    queryset = Activity.objects.filter(is_delete=0, status__gt=2)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class ActivityUpdateView(GenericAPIView, UpdateModelMixin):
    """修改一个活动"""
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
        queryset = Activity.objects.filter(is_delete=0, status__in=[3, 4], user_id=self.request.user.id)
        if activity_level == 3:
            queryset = Activity.objects.filter(is_delete=0, status__in=[3, 4])
        return queryset


class ActivityPublishView(GenericAPIView, UpdateModelMixin):
    """通过申请"""
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
        logger.error('[ActivityPublishView] Fail to validate when publishing activity, the error messages are {}'.
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
        logger.info('活动通过审核')
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 201, 'msg': '活动通过审核，已发布', 'access': access})


class ActivityRejectView(GenericAPIView, UpdateModelMixin):
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
        logger.error('[ActivityRejectView] Fail to validate when rejecting activity, the error messages are {}'.
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


class ActivityDelView(GenericAPIView, UpdateModelMixin):
    """删除一个活动"""
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
        logger.error('[ActivityDelView] Fail to validate when deleting activity, the error messages are {}'.
                     format(','.join(err_msgs)))
        return False, None

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_DELETE,
                           OperationLogDesc.OP_DESC_ACTIVITY_DELETE_CODE) as log_context:
            log_context.log_vars = [kwargs.get('pk')]
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


class ActivityDraftView(GenericAPIView, CreateModelMixin):
    """创建活动草案"""
    serializer_class = ActivitySerializer
    queryset = Activity.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def validate(self, request):
        now_time = datetime.datetime.now()
        err_msgs = []
        data = self.request.data
        title = data.get('title')
        date = data.get('date')
        activity_type = data.get('activity_type')
        synopsis = data.get('synopsis')
        poster = data.get('poster')
        register_url = data.get('register_url')
        address = data.get('address')
        detail_address = data.get('detail_address')
        longitude = data.get('longitude')
        latitude = data.get('latitude')
        start = data.get('start')
        end = data.get('end')
        schedules = data.get('schedules')
        try:
            if date <= datetime.datetime.strftime(now_time, '%Y-%m-%d'):
                err_msgs.append('The start date should be earlier than tomorrow')
            start_time = datetime.datetime.strptime(' '.join([date, start]), '%Y-%m-%d %H:%M')
            end_time = datetime.datetime.strptime(' '.join([date, end]), '%Y-%m-%d %H:%M')
            if start_time <= now_time:
                err_msgs.append('The start time should not be later than the current time')
            if start_time >= end_time:
                err_msgs.append('The start time should not be later than the end time')
        except ValueError:
            err_msgs.append('Invalid datetime params')
        if not title:
            err_msgs.append('Activity title could not be empty')
        if activity_type not in [offline, online]:
            err_msgs.append('Invalid activity type')
        if poster not in range(1, 5):
            err_msgs.append('Invalid poster')
        if not register_url.startswith('https://'):
            err_msgs.append('Invalid register url')
        if err_msgs:
            logger.error('[ActivityView] Fail to validate when creating activity, the error messages are {}'.format(
                ','.join(err_msgs)))
            return False, None
        validated_data = {
            'title': title,
            'date': date,
            'activity_type': activity_type,
            'synopsis': synopsis,
            'poster': poster,
            'register_url': register_url,
            'address': address,
            'detail_address': detail_address,
            'longitude': longitude,
            'latitude': latitude,
            'start': start,
            'end': end,
            'schedules': schedules
        }
        return True, validated_data

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_MEETING,
                           OperationLogType.OP_TYPE_CREATE,
                           OperationLogDesc.OP_DESC_ACTIVITY_CREATE_DRAFT_CODE) as log_context:
            log_context.log_vars = [request.data.get("title")]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        is_validated, data = self.validate(request)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        title = data.get('title')
        date = data.get('date')
        activity_type = data.get('activity_type')
        synopsis = data.get('synopsis')
        poster = data.get('poster')
        user_id = self.request.user.id
        register_url = data.get('register_url')
        # 线下活动
        if activity_type == offline:
            address = data.get('address')
            detail_address = data.get('detail_address')
            longitude = data.get('longitude')
            latitude = data.get('latitude')
            Activity.objects.create(
                title=title,
                date=date,
                activity_type=activity_type,
                synopsis=synopsis,
                address=address,
                detail_address=detail_address,
                longitude=longitude,
                latitude=latitude,
                schedules=json.dumps(data.get('schedules')),
                poster=poster,
                user_id=user_id,
                register_url=register_url
            )
        # 线上活动
        if activity_type == online:
            start = data.get('start')
            end = data.get('end')
            Activity.objects.create(
                title=title,
                date=date,
                start=start,
                end=end,
                activity_type=activity_type,
                synopsis=synopsis,
                schedules=json.dumps(data.get('schedules')),
                poster=poster,
                user_id=user_id,
                register_url=register_url
            )
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 201, 'msg': '活动草案创建成功！', 'access': access})


class ActivitiesDraftView(GenericAPIView, ListModelMixin):
    """活动草案列表"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Activity.objects.filter(is_delete=0, status=1, user_id=self.request.user.id).order_by('-date', 'id')
        return queryset


class SponsorActivityDraftView(GenericAPIView, RetrieveModelMixin, DestroyModelMixin):
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
        queryset = Activity.objects.filter(is_delete=0, status=1, user_id=self.request.user.id).order_by('-date', 'id')
        return queryset


class DraftUpdateView(GenericAPIView, UpdateModelMixin):
    """修改活动草案"""
    serializer_class = ActivityDraftUpdateSerializer
    queryset = Activity.objects.filter(is_delete=0, status=1)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def validate(self, request):
        now_time = datetime.datetime.now()
        err_msgs = []
        activity_id = self.kwargs.get('pk')
        user_id = self.request.user.id
        data = self.request.data
        title = data.get('title')
        date = data.get('date')
        activity_type = data.get('activity_type')
        synopsis = data.get('synopsis')
        poster = data.get('poster')
        register_url = data.get('register_url')
        address = data.get('address')
        detail_address = data.get('detail_address')
        longitude = data.get('longitude')
        latitude = data.get('latitude')
        start = data.get('start')
        end = data.get('end')
        schedules = data.get('schedules')
        if not Activity.objects.filter(id=activity_id, user_id=user_id, status=1):
            err_msgs.append('Invalid activity id')
        try:
            if date <= datetime.datetime.strftime(now_time, '%Y-%m-%d'):
                err_msgs.append('The start date should be earlier than tomorrow')
            start_time = datetime.datetime.strptime(' '.join([date, start]), '%Y-%m-%d %H:%M')
            end_time = datetime.datetime.strptime(' '.join([date, end]), '%Y-%m-%d %H:%M')
            if start_time <= now_time:
                err_msgs.append('The start time should not be later than the current time')
            if start_time >= end_time:
                err_msgs.append('The start time should not be later than the end time')
        except ValueError:
            err_msgs.append('Invalid datetime params')
        if not title:
            err_msgs.append('Activity title could not be empty')
        if activity_type not in [offline, online]:
            err_msgs.append('Invalid activity type')
        if poster not in range(1, 5):
            err_msgs.append('Invalid poster')
        if not register_url.startswith('https://'):
            err_msgs.append('Invalid register url')
        if err_msgs:
            logger.error('[ActivityView] Fail to validate when creating activity, the error messages are {}'.format(
                ','.join(err_msgs)))
            return False, None
        validated_data = {
            'title': title,
            'date': date,
            'activity_type': activity_type,
            'synopsis': synopsis,
            'poster': poster,
            'register_url': register_url,
            'address': address,
            'detail_address': detail_address,
            'longitude': longitude,
            'latitude': latitude,
            'start': start,
            'end': end,
            'schedules': schedules
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
        is_validated, data = self.validate(request)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        activity_id = self.kwargs.get('pk')
        title = data.get('title')
        date = data.get('date')
        activity_type = data.get('activity_type')
        synopsis = data.get('synopsis')
        poster = data.get('poster')
        user_id = self.request.user.id
        register_url = data.get('register_url')
        if activity_type == offline:
            address = data.get('address')
            detail_address = data.get('detail_address')
            longitude = data.get('longitude')
            latitude = data.get('latitude')
            Activity.objects.filter(id=activity_id, user_id=user_id).update(
                title=title,
                date=date,
                activity_type=activity_type,
                synopsis=synopsis,
                address=address,
                detail_address=detail_address,
                longitude=longitude,
                latitude=latitude,
                schedules=json.dumps(data.get('schedules')),
                poster=poster,
                register_url=register_url
            )
        if activity_type == online:
            start = data.get('start')
            end = data.get('end')
            Activity.objects.filter(id=activity_id, user_id=user_id).update(
                title=title,
                date=date,
                start=start,
                end=end,
                activity_type=activity_type,
                synopsis=synopsis,
                schedules=json.dumps(data.get('schedules')),
                poster=poster,
                register_url=register_url
            )
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 201, 'msg': '修改并保存活动草案', 'access': access})


class DraftPublishView(GenericAPIView, UpdateModelMixin):
    """修改活动草案并申请发布"""
    serializer_class = ActivityDraftUpdateSerializer
    queryset = Activity.objects.filter(is_delete=0, status=1)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def validate(self, request):
        now_time = datetime.datetime.now()
        err_msgs = []
        activity_id = self.kwargs.get('pk')
        user_id = self.request.user.id
        data = self.request.data
        title = data.get('title')
        date = data.get('date')
        activity_type = data.get('activity_type')
        synopsis = data.get('synopsis')
        poster = data.get('poster')
        register_url = data.get('register_url')
        address = data.get('address')
        detail_address = data.get('detail_address')
        longitude = data.get('longitude')
        latitude = data.get('latitude')
        start = data.get('start')
        end = data.get('end')
        schedules = data.get('schedules')
        if not Activity.objects.filter(id=activity_id, user_id=user_id, status=1):
            err_msgs.append('Invalid activity id')
        try:
            if date <= datetime.datetime.strftime(now_time, '%Y-%m-%d'):
                err_msgs.append('The start date should be earlier than tomorrow')
            start_time = datetime.datetime.strptime(' '.join([date, start]), '%Y-%m-%d %H:%M')
            end_time = datetime.datetime.strptime(' '.join([date, end]), '%Y-%m-%d %H:%M')
            if start_time <= now_time:
                err_msgs.append('The start time should not be later than the current time')
            if start_time >= end_time:
                err_msgs.append('The start time should not be later than the end time')
        except ValueError:
            err_msgs.append('Invalid datetime params')
        if not title:
            err_msgs.append('Activity title could not be empty')
        if activity_type not in [offline, online]:
            err_msgs.append('Invalid activity type')
        if poster not in range(1, 5):
            err_msgs.append('Invalid poster')
        if not register_url.startswith('https://'):
            err_msgs.append('Invalid register url')
        if err_msgs:
            logger.error('[ActivityView] Fail to validate when creating activity, the error messages are {}'.format(
                ','.join(err_msgs)))
            return False, None
        validated_data = {
            'title': title,
            'date': date,
            'activity_type': activity_type,
            'synopsis': synopsis,
            'poster': poster,
            'register_url': register_url,
            'address': address,
            'detail_address': detail_address,
            'longitude': longitude,
            'latitude': latitude,
            'start': start,
            'end': end,
            'schedules': schedules
        }
        return True, validated_data

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_ACTIVITY_PUBLISH_DRAFT_CODE) as log_context:
            log_context.log_vars = [kwargs.get('pk')]
            ret = self.update(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def update(self, request, *args, **kwargs):
        is_validated, data = self.validate(request)
        if not is_validated:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        activity_id = self.kwargs.get('pk')
        data = self.request.data
        title = data.get('title')
        date = data.get('date')
        activity_type = data['activity_type']
        synopsis = data.get('synopsis')
        poster = data.get('poster')
        user_id = self.request.user.id
        if activity_type == offline:
            address = data.get('address')
            detail_address = data.get('detail_address')
            longitude = data.get('longitude')
            latitude = data.get('latitude')
            Activity.objects.filter(id=activity_id, user_id=user_id).update(
                title=title,
                date=date,
                activity_type=activity_type,
                synopsis=synopsis,
                address=address,
                detail_address=detail_address,
                longitude=longitude,
                latitude=latitude,
                schedules=json.dumps(data.get('schedules')),
                poster=poster,
                status=2
            )
        if activity_type == online:
            start = data.get('start')
            end = data.get('end')
            Activity.objects.filter(id=activity_id, user_id=user_id).update(
                title=title,
                date=date,
                start=start,
                end=end,
                activity_type=activity_type,
                synopsis=synopsis,
                schedules=json.dumps(data.get('schedules')),
                poster=poster,
                status=2
            )
        access = refresh_access(self.request.user)
        return JsonResponse({'code': 201, 'msg': '申请发布活动', 'access': access})


class SponsorActivitiesPublishingView(GenericAPIView, ListModelMixin):
    """发布中的活动"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Activity.objects.filter(is_delete=0, status=2, user_id=self.request.user.id).order_by('-date', 'id')
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


class ActivityCollectDelView(GenericAPIView, DestroyModelMixin):
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


class MyActivityCollectionsView(GenericAPIView, ListModelMixin):
    """我收藏的活动(列表)"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        user_id = self.request.user.id
        collection_lst = ActivityCollect.objects.filter(user_id=user_id).values_list('activity', flat=True)
        queryset = Activity.objects.filter(is_delete=0, id__in=collection_lst).order_by('-date', 'id')
        return queryset


class CountActivitiesView(GenericAPIView, ListModelMixin):
    """各类活动计数"""
    queryset = Activity.objects.filter(is_delete=0, status__gt=2).order_by('-date', 'id')
    filter_backends = [SearchFilter]
    search_fields = ['title']

    def get(self, request, *args, **kwargs):
        search = self.request.GET.get('search')
        activity_type = self.request.GET.get('activity_type')
        if search and not activity_type:
            self.queryset = self.queryset.filter(title__icontains=search)
        if activity_type:
            try:
                if int(activity_type) == 1:
                    self.queryset = self.queryset.filter(activity_type=1)
                if int(activity_type) == 2:
                    self.queryset = self.queryset.filter(activity_type=2)
                if int(activity_type) == 1 and search:
                    self.queryset = self.queryset.filter(activity_type=1).filter(title__icontains=search)
                if int(activity_type) == 2 and search:
                    self.queryset = self.queryset.filter(activity_type=2).filter(title__icontains=search)
            except TypeError:
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
    authentication_classes = (CustomAuthentication,)

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


class ActivitiesDataView(GenericAPIView, ListModelMixin):
    """活动日历数据"""
    queryset = Activity.objects.filter(is_delete=0, status__in=[3, 4, 5])

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
                    'start_date': date,
                    'timeData': [{
                        'id': activity.id,
                        'title': activity.title,
                        'start_date': activity.date,
                        'end_date': activity.date,
                        'activity_type': activity.activity_type,
                        'address': activity.address,
                        'detail_address': activity.detail_address,
                        'longitude': activity.longitude,
                        'latitude': activity.latitude,
                        'synopsis': activity.synopsis,
                        'sign_url': activity.sign_url,
                        'replay_url': activity.replay_url,
                        'register_url': activity.register_url,
                        'poster': activity.poster,
                        'wx_code': activity.wx_code,
                        'schedules': json.loads(activity.schedules)
                    } for activity in Activity.objects.filter(is_delete=0, date=date)]
                }
            )
        return Response({'tableData': tableData})
