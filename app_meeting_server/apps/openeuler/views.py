import datetime
import logging
import json
import secrets
import time
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from rest_framework.filters import SearchFilter
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin, DestroyModelMixin, \
    UpdateModelMixin
from app_meeting_server.utils.my_pagination import MyPagination
from openeuler.models import User, Group, Meeting, GroupUser, Collect, Video, Record, \
    Activity, ActivityCollect
from app_meeting_server.utils.permissions import MaintainerPermission, MeetigsAdminPermission, \
    ActivityAdminPermission, SponsorPermission, QueryPermission, AdminPermission, MaintainerAndAdminPermission
from openeuler.serializers import LoginSerializer, GroupsSerializer, MeetingSerializer, \
    UsersSerializer, UserSerializer, GroupUserAddSerializer, UsersInGroupSerializer, \
    UserGroupSerializer, MeetingListSerializer, GroupUserDelSerializer, UserInfoSerializer, \
    MeetingsDataSerializer, AllMeetingsSerializer, CollectSerializer, SponsorSerializer, ActivitySerializer, \
    ActivitiesSerializer, ActivityDraftUpdateSerializer, ActivityUpdateSerializer, \
    ActivityCollectSerializer, ActivityRetrieveSerializer
from openeuler.utils.send_email import sendmail
from rest_framework import permissions
from openeuler.utils import gene_wx_code, drivers, send_cancel_email
from app_meeting_server.utils.auth import CustomAuthentication, CustomAuthenticationWithoutPolicyAgreen
from app_meeting_server.utils import wx_apis
from app_meeting_server.utils.operation_log import LoggerContext, OperationLogModule, OperationLogDesc, \
    OperationLogType, PolicyLoggerContext
from app_meeting_server.utils.common import get_cur_date, decrypt_openid, clear_token, refresh_token_and_refresh_token, \
    start_thread, get_version_params
from app_meeting_server.utils.ret_api import MyValidationError, ret_json, ret_access_json
from app_meeting_server.utils.check_params import check_group_id_and_user_ids, \
    check_user_ids, check_activity_params, check_meetings_params, check_schedules_string, check_date, check_type, \
    check_refresh_token, check_int, check_gitee_name
from app_meeting_server.utils.ret_code import RetCode
from rest_framework_simplejwt.views import TokenRefreshView

logger = logging.getLogger('log')
offline = 1
online = 2


# ------------------------------common view------------------------------
class PingView(GenericAPIView):
    """心跳"""

    def get(self, request, *args):
        return ret_json(code=200, msg='the status is ok')


# ------------------------------user view------------------------------
class LoginView(GenericAPIView, CreateModelMixin):
    """用户注册与授权登陆"""
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        policy_version, app_policy_version, cur_date = get_version_params()
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_LOGIN,
                           OperationLogDesc.OP_DESC_USER_LOGIN_CODE) as log_context, \
                PolicyLoggerContext(policy_version, app_policy_version, cur_date) as policy_log_context:
            log_context.log_vars = ["anonymous"]
            ret = self.create(request, *args, **kwargs)
            log_context.request.user = User.objects.filter(id=ret.data.get("user_id")).first()
            log_context.log_vars = [str(ret.data.get("user_id"))]
            log_context.result = ret
            policy_log_context.result = True
            return ret


class RefreshView(TokenRefreshView):
    """用户刷新token"""

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_REFRESH,
                           OperationLogDesc.OP_DESC_USER_REFRESH_CODE) as log_context:
            log_context.log_vars = ["anonymous"]
            refresh = request.data.get("refresh")
            cur_user = check_refresh_token(refresh)
            log_context.log_vars = [cur_user.id]
            access_token, refresh_token = refresh_token_and_refresh_token(cur_user)
            ret_dict = {
                "refresh": refresh_token,
                "access": access_token
            }
            ret = ret_json(**ret_dict)
            log_context.result = ret
            return ret


class LogoutView(GenericAPIView):
    """登出"""
    authentication_classes = (CustomAuthenticationWithoutPolicyAgreen,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_LOGOUT,
                           OperationLogDesc.OP_DESC_USER_LOGOFF_CODE) as log_context:
            log_context.log_vars = [request.user.id]
            clear_token(request.user)
            ret = ret_json(msg="User logged out")
            logger.info('User {} logged out'.format(request.user.id))
            log_context.result = ret
            return ret


class LogoffView(GenericAPIView):
    """注销"""
    authentication_classes = (CustomAuthenticationWithoutPolicyAgreen,)
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
        user_id = request.user.id
        if request.user.level == MeetigsAdminPermission.level or \
                request.user.activity_level == ActivityAdminPermission.activity_level:
            raise MyValidationError(RetCode.STATUS_START_ONLY_ONE_ADMIN)
        cur_date = get_cur_date()
        expired_date = cur_date + datetime.timedelta(days=settings.LOGOFF_EXPIRED)
        User.objects.filter(id=user_id).update(is_delete=1, logoff_time=expired_date)
        clear_token(request.user)
        ret = ret_json(msg="User logged off")
        logger.info('User {} logged off'.format(user_id))
        return ret


class AgreePrivacyPolicyView(GenericAPIView, UpdateModelMixin):
    """同意更新隐私声明"""
    authentication_classes = (CustomAuthenticationWithoutPolicyAgreen,)
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
        policy_version = settings.PRIVACY_POLICY_VERSION
        app_policy_version = settings.PRIVACY_APP_POLICY_VERSION
        cur_date = get_cur_date()
        with PolicyLoggerContext(policy_version, app_policy_version, cur_date) as policy_log_context:
            if User.objects.get(id=self.request.user.id).agree_privacy_policy:
                msg = 'The user {} has signed privacy policy agreement already.'.format(self.request.user.id)
                logger.error(msg)
                raise MyValidationError(RetCode.STATUS_USER_HAS_SIGNED_POLICY)
            User.objects.filter(id=self.request.user.id).update(agree_privacy_policy=True,
                                                                agree_privacy_policy_time=cur_date,
                                                                agree_privacy_policy_version=policy_version,
                                                                agree_privacy_app_policy_version=app_policy_version)
            policy_log_context.result = True
        resp = ret_access_json(request.user, msg="Agree to privacy statement")
        return resp


class RevokeAgreementView(GenericAPIView):
    """撤销同意隐私声明"""
    authentication_classes = (CustomAuthenticationWithoutPolicyAgreen,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_USER_REVOKE_AGREEMENT_CODE) as log_context:
            log_context.log_vars = [request.user.id]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        policy_version = settings.PRIVACY_POLICY_VERSION
        app_policy_version = settings.PRIVACY_APP_POLICY_VERSION
        cur_date = get_cur_date()
        user_id = request.user.id
        with PolicyLoggerContext(policy_version, app_policy_version, cur_date, is_agreen=False) as policy_log_context:
            if request.user.level == MeetigsAdminPermission.level or \
                    request.user.activity_level == ActivityAdminPermission.activity_level:
                raise MyValidationError(RetCode.STATUS_START_POLICY_ONLY_ONE_ADMIN)
            with transaction.atomic():
                User.objects.filter(id=user_id).update(agree_privacy_policy=False,
                                                       revoke_agreement_time=cur_date,
                                                       gitee_name=None,
                                                       level=1,
                                                       activity_level=1)
                Meeting.objects.filter(user__id=user_id).update(emaillist=None, sponsor='')
                GroupUser.objects.filter(user_id=user_id).delete()
                ActivityCollect.objects.filter(user_id=user_id).delete()
                Collect.objects.filter(user_id=user_id).delete()
            policy_log_context.result = True
        clear_token(request.user)
        resp = ret_json(msg="Revoke agreement of privacy policy")
        return resp


class GroupsView(GenericAPIView, ListModelMixin):
    """查询所有SIG组的名称"""
    serializer_class = GroupsSerializer
    queryset = Group.objects.all().order_by('group_name')
    filter_backends = [SearchFilter]
    search_fields = ['group_name']
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MeetigsAdminPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class UsersIncludeView(GenericAPIView, ListModelMixin):
    """查询所选SIG组的所有成员"""
    serializer_class = UsersInGroupSerializer
    queryset = User.objects.all()
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MeetigsAdminPermission,)
    pagination_class = MyPagination

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        group_users = GroupUser.objects.filter(group_id=self.kwargs['pk']).all()
        ids = [x.user_id for x in group_users]
        user = User.objects.filter(id__in=ids, is_delete=0).order_by('nickname')
        return user


class UsersExcludeView(GenericAPIView, ListModelMixin):
    """查询不在该组的所有成员"""
    serializer_class = UsersSerializer
    queryset = User.objects.all().order_by('nickname')
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MeetigsAdminPermission,)
    pagination_class = MyPagination

    def get(self, request, *args, **kwargs):
        pk = self.kwargs["pk"]
        if Group.objects.filter(id=pk).count() == 0:
            logger.error("The Group {} is not exist".format(pk))
            raise MyValidationError(RetCode.STATUS_SIG_GROUP_NOT_EXIST)
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        group_users = GroupUser.objects.filter(group_id=self.kwargs['pk']).all()
        ids = [x.user_id for x in group_users]
        user = User.objects.filter(is_delete=0).exclude(id__in=ids).\
            exclude(level=MeetigsAdminPermission.level).order_by('nickname')
        return user


class GroupUserAddView(GenericAPIView, CreateModelMixin):
    """SIG组批量新增成员"""
    serializer_class = GroupUserAddSerializer
    queryset = GroupUser.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MeetigsAdminPermission,)

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_USER_ADD_GROUP_CODE) as log_context:
            log_context.log_vars = [request.data.get("ids"), request.data.get("group_id")]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        super(GroupUserAddView, self).create(request, *args, **kwargs)
        return ret_access_json(request.user)


class GroupUserDelView(GenericAPIView, CreateModelMixin):
    """批量删除组成员"""
    serializer_class = GroupUserDelSerializer
    queryset = GroupUser.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MeetigsAdminPermission,)

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_USER_REMOVE_GROUP_CODE) as log_context:
            log_context.log_vars = [request.data.get("ids"), request.data.get("group_id")]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        group_id = request.data.get('group_id')
        user_ids = request.data.get('ids')
        new_group_id, new_list_ids = check_group_id_and_user_ids(group_id, user_ids, GroupUser, Group)
        count_user = User.objects.filter(id__in=new_list_ids).filter(is_delete=0).count()
        if count_user != len(new_list_ids):
            logger.info("GroupUserDelView find anonymous or be deleted")
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        GroupUser.objects.filter(group_id=new_group_id, user_id__in=new_list_ids).delete()
        return ret_access_json(request.user)


class UserInfoView(GenericAPIView, RetrieveModelMixin):
    """查询本机用户的level和gitee_name"""
    serializer_class = UserInfoSerializer
    queryset = User.objects.filter(is_delete=0)
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)

    def get(self, request, *args, **kwargs):
        user_id = kwargs.get('pk')
        if user_id != request.user.id:
            logger.warning('user_id did not match.user_id:{}, request.user.id:{}'.format(user_id, request.user.id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        return self.retrieve(request, *args, **kwargs)


class SponsorsView(GenericAPIView, ListModelMixin):
    """活动发起人列表"""
    serializer_class = SponsorSerializer
    queryset = User.objects.filter(activity_level=2, is_delete=0).order_by("nickname")
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)
    pagination_class = MyPagination

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class NonSponsorView(GenericAPIView, ListModelMixin):
    """非活动发起人列表"""
    serializer_class = SponsorSerializer
    queryset = User.objects.filter(activity_level=1, is_delete=0).order_by("nickname")
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)
    pagination_class = MyPagination

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class SponsorAddView(GenericAPIView, CreateModelMixin):
    """批量添加活动发起人"""
    queryset = User.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_USER_ADD_ACTIVITY_SPONSOR_CODE) as log_context:
            log_context.log_vars = [request.data.get('ids')]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        user_ids = request.data.get('ids')
        new_user_ids = check_user_ids(user_ids)
        match_queryset = User.objects.filter(id__in=new_user_ids, activity_level=1, is_delete=0).count()
        if len(new_user_ids) != match_queryset:
            logger.error("The input ids: {}, parse result {} not eq query result {}".format(user_ids, new_user_ids,
                                                                                            match_queryset))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        User.objects.filter(id__in=new_user_ids, activity_level=1, is_delete=0).update(activity_level=2)
        return ret_access_json(request.user)


class SponsorDelView(GenericAPIView, CreateModelMixin):
    """批量删除组成员"""
    queryset = GroupUser.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_USER_REMOVE_ACTIVITY_SPONSOR_CODE) as log_context:
            log_context.log_vars = [request.data.get('ids')]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        user_ids = request.data.get('ids')
        new_user_ids = check_user_ids(user_ids)
        match_queryset = User.objects.filter(id__in=new_user_ids, activity_level=2, is_delete=0).count()
        if match_queryset != len(new_user_ids):
            logger.error("The input ids: {}, parse result {} not eq query result {}".format(user_ids, new_user_ids,
                                                                                            match_queryset))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        User.objects.filter(id__in=new_user_ids, activity_level=2, is_delete=0).update(activity_level=1)
        return ret_access_json(request.user)


class UserView(GenericAPIView, UpdateModelMixin):
    """更新用户gitee_name"""
    serializer_class = UserSerializer
    queryset = User.objects.filter(is_delete=0)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MeetigsAdminPermission,)

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_USER_MODIFY_CODE) as log_context:
            log_context.log_vars = [request.user.id]
            ret = self.update(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def update(self, request, *args, **kwargs):
        gitee_name = request.data.get("gitee_name")
        if gitee_name:
            check_gitee_name(gitee_name)
        super(UserView, self).update(request, *args, **kwargs)
        return ret_access_json(request.user)


class UserGroupView(GenericAPIView, ListModelMixin):
    """查询该用户的SIG组以及该组的etherpad"""
    serializer_class = UserGroupSerializer
    queryset = GroupUser.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        user_group = GroupUser.objects.filter(user_id=self.kwargs['pk']).all()
        return user_group


class MyCountsView(GenericAPIView, ListModelMixin):
    """我的各类计数"""
    queryset = Activity.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)

    def get(self, request, *args, **kwargs):
        user_id = self.request.user.id
        level = self.request.user.level
        activity_level = self.request.user.activity_level

        # shared
        collected_meetings_count = Meeting.objects.filter(is_delete=0, id__in=(Collect.objects.filter(user_id=user_id).
                                                                               values_list('meeting_id',
                                                                                           flat=True))).count()
        collected_activities_count = Activity.objects.filter(is_delete=0,
                                                             id__in=(ActivityCollect.objects.filter(user_id=user_id).
                                                                     values_list('activity_id', flat=True))).count()
        res = {
            'collected_meetings_count': collected_meetings_count,
            'collected_activities_count': collected_activities_count
        }
        # permission limited
        if level == 2:
            created_meetings_count = Meeting.objects.filter(is_delete=0, user_id=user_id).count()
            res['created_meetings_count'] = created_meetings_count
        elif level == 3:
            created_meetings_count = Meeting.objects.filter(is_delete=0).count()
            res['created_meetings_count'] = created_meetings_count
        if activity_level == 2:
            published_activities_count = Activity.objects.filter(is_delete=0, status__gt=2, user_id=user_id).count()
            drafts_count = Activity.objects.filter(is_delete=0, status=1, user_id=user_id).count()
            publishing_activities_count = Activity.objects.filter(is_delete=0, status=2, user_id=user_id).count()
            res['published_activities_count'] = published_activities_count
            res['drafts_count'] = drafts_count
            res['publishing_activities_count'] = publishing_activities_count
        elif activity_level == 3:
            published_activities_count = Activity.objects.filter(is_delete=0, status__gt=2).count()
            drafts_count = Activity.objects.filter(is_delete=0, status=1, user_id=user_id).count()
            publishing_activities_count = Activity.objects.filter(is_delete=0, status=2).count()
            res['published_activities_count'] = published_activities_count
            res['drafts_count'] = drafts_count
            res['publishing_activities_count'] = publishing_activities_count
        return JsonResponse(res)


# ------------------------------meeting view------------------------------
class MeetingsWeeklyView(GenericAPIView, ListModelMixin):
    """查询前后一周的所有会议"""
    serializer_class = MeetingListSerializer
    queryset = Meeting.objects.filter(is_delete=0)
    filter_backends = [SearchFilter]
    search_fields = ['topic']
    pagination_class = MyPagination

    def get(self, request, *args, **kwargs):
        group_name = self.request.GET.get('group_name')
        if group_name:
            self.queryset = self.queryset.filter(group__group_name=group_name)
        self.queryset = self.queryset.filter((Q(
            date__gte=str(datetime.datetime.now() - datetime.timedelta(days=7))[:10]) & Q(
            date__lte=str(datetime.datetime.now() + datetime.timedelta(days=7))[:10]))).order_by('-date', 'start')
        return self.list(request, *args, **kwargs)


class MeetingsGroupView(GenericAPIView, ListModelMixin):
    serializer_class = GroupsSerializer
    queryset = Group.objects.all()

    def get(self, request, *args, **kwargs):
        meeting_ids = Meeting.objects.filter(is_delete=0).filter((Q(
            date__gte=str(datetime.datetime.now() - datetime.timedelta(days=7))[:10]) & Q(
            date__lte=str(datetime.datetime.now() + datetime.timedelta(days=7))[:10]))).values_list("group_id",
                                                                                                    flat=True)
        self.queryset = self.queryset.filter(id__in=meeting_ids).order_by('group_name')
        return self.list(request, *args, **kwargs)


class MeetingsDailyView(GenericAPIView, ListModelMixin):
    """查询本日的所有会议"""
    serializer_class = MeetingListSerializer
    queryset = Meeting.objects.filter(is_delete=0)
    pagination_class = MyPagination

    def get(self, request, *args, **kwargs):
        self.queryset = self.queryset.filter(date=str(datetime.datetime.now())[:10]).order_by('start')
        return self.list(request, *args, **kwargs)


class MeetingsRecentlyView(GenericAPIView, ListModelMixin):
    """查询最近的会议"""
    serializer_class = MeetingListSerializer
    queryset = Meeting.objects.filter(is_delete=0)
    pagination_class = MyPagination

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
    permission_classes = (MaintainerAndAdminPermission,)

    def delete(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_MEETING,
                           OperationLogType.OP_TYPE_DELETE,
                           OperationLogDesc.OP_DESC_MEETING_DELETE_CODE) as log_context:
            log_context.log_vars = [kwargs.get('mid')]
            ret = self.destroy(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def destroy(self, request, *args, **kwargs):
        user_id = request.user.id
        mid = self.kwargs.get('mid')
        if Meeting.objects.filter(mid=mid, is_delete=0).count() == 0:
            logger.error('That meeting :{} is not exist'.format(mid))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        elif not (Meeting.objects.filter(mid=mid, user_id=user_id).count() != 0 or User.objects.filter(id=user_id,
                                                                                                       level=3).count() != 0):
            logger.error('User {} has no access to delete meeting {}'.format(user_id, mid))
            raise MyValidationError(RetCode.STATUS_USER_HAS_NO_PERMISSIONS)

        meeting = Meeting.objects.get(mid=mid)
        cur_date = get_cur_date()
        start_date_str = "{} {}".format(meeting.date, meeting.start)
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d %H:%M")
        if int((start_date - cur_date).total_seconds()) < 1 * 60 * 60:
            raise MyValidationError(RetCode.STATUS_MEETING_CANNNOT_BE_DELETE)

        # 删除会议
        drivers.cancelMeeting(mid)

        # 会议作软删除
        Meeting.objects.filter(mid=mid).update(is_delete=1)
        meeting_id = meeting.id
        mid = meeting.mid
        logger.info('{} has canceled the meeting which mid was {}'.format(user_id, mid))

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
                openid = decrypt_openid(encrypt_openid)
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
        return ret_access_json(request.user)


class SigMeetingsDataView(GenericAPIView, ListModelMixin):
    """网页SIG组日历数据"""
    serializer_class = MeetingsDataSerializer
    queryset = Meeting.objects.filter(is_delete=0).order_by('date', 'start')

    def get(self, request, *args, **kwargs):
        group_name = kwargs.get('gn')
        queryset = self.filter_queryset(self.get_queryset()).filter(group_name=group_name).filter((Q(
            date__gte=str(datetime.datetime.now() - datetime.timedelta(days=180))[:10]) & Q(
            date__lte=str(datetime.datetime.now() + datetime.timedelta(days=30))[:10]))).values()
        my_paginate = MyPagination()
        queryset = my_paginate.paginate_queryset(queryset, request)
        table_data = []
        date_list = []
        for query in queryset:
            date_list.append(query.get('date'))
        date_list = sorted(list(set(date_list)))
        records = Record.objects.filter(platform='bilibili', url__isnull=False).values()
        record_dict = {}
        for record in records:
            if record['platform'] == 'bilibili' and record['url']:
                record_dict[record['mid']] = record['url']
        for date in date_list:
            time_data = []
            for meeting in queryset:
                if meeting['date'] != date:
                    continue
                time_data.append({
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
            table_data.append({
                'date': date,
                'timeData': time_data
            })
        return my_paginate.get_paginated_response(table_data)


class MeetingsView(GenericAPIView, CreateModelMixin):
    """创建会议"""
    serializer_class = MeetingSerializer
    queryset = Meeting.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MaintainerPermission,)

    def post(self, request, *args, **kwargs):
        policy_version, app_policy_version, cur_date = get_version_params()
        with LoggerContext(request, OperationLogModule.OP_MODULE_MEETING,
                           OperationLogType.OP_TYPE_CREATE,
                           OperationLogDesc.OP_DESC_MEETING_CREATE_CODE) as log_context, \
                PolicyLoggerContext(policy_version, app_policy_version, cur_date) as policy_log_context:
            log_context.log_vars = [request.data.get('topic')]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            policy_log_context.result = True
            return ret

    def create(self, request, *args, **kwargs):
        t1 = time.time()
        data = check_meetings_params(request, Group)
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
        summary = data.get('summary')
        user_id = data.get('user_id')
        group_id = data.get('group_id')
        record = data.get('record')
        etherpad = data.get('etherpad')
        # 1.查询待创建的会议与现有的预定会议是否冲突
        start_search = datetime.datetime.strftime(
            (datetime.datetime.strptime(start, '%H:%M') - datetime.timedelta(minutes=30)),
            '%H:%M')
        end_search = datetime.datetime.strftime(
            (datetime.datetime.strptime(end, '%H:%M') + datetime.timedelta(minutes=30)),
            '%H:%M')
        host_ids = list(host_dict.keys())
        meetings = Meeting.objects.filter(is_delete=0, date=date, end__gt=start_search, start__lt=end_search,
                                          mplatform=platform).values()
        unavailable_host_ids = [meeting['host_id'] for meeting in meetings]
        available_host_id = list(set(host_ids) - set(unavailable_host_ids))
        if len(available_host_id) == 0:
            logger.warning('No available host:{} yet'.format(platform))
            raise MyValidationError(RetCode.STATUS_MEETING_NO_AVAILABLE_HOST)
        # 2.从available_host_id中随机生成一个host_id,并在host_dict中取出
        host_id = secrets.choice(available_host_id)
        host = host_dict[host_id]
        status, content = drivers.createMeeting(platform, date, start, end, topic, host, record)
        if status not in [200, 201]:
            logger.error("Failed to create meeting, and code is {}".format(str(status)))
            raise MyValidationError(RetCode.STATUS_MEETING_FAILED_CREATE)
        mid = content['mid']
        mmid = content.get("mmid")
        start_url = content.get('start_url')
        join_url = content['join_url']
        host_id = content['host_id']
        timezone = content['timezone'] if 'timezone' in content else 'Asia/Shanghai'
        # 3.数据库生成数据
        Meeting.objects.create(
            mid=mid,
            mmid=mmid,
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
        logger.info('created a {} meeting which mid is {}.'.format(platform, mid))
        logger.info('meeting info: {},{}-{},{}'.format(date, start, end, topic))
        # 4.发送email
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
        start_thread(sendmail, m, record)
        meeting = Meeting.objects.get(mid=mid)
        t3 = time.time()
        print('total waste: {}'.format(t3 - t1))
        resp = ret_access_json(request.user, id=meeting.id)
        return resp


class MyMeetingsView(GenericAPIView, ListModelMixin):
    """查询我创建的所有会议"""
    serializer_class = MeetingListSerializer
    queryset = Meeting.objects.all().filter(is_delete=0)
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)
    pagination_class = MyPagination

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
    queryset = Meeting.objects.all().order_by('-date', 'start')
    filter_backends = [SearchFilter]
    search_fields = ['is_delete', 'group_name', 'sponsor', 'date', 'start', 'end']
    permission_classes = (QueryPermission,)
    pagination_class = MyPagination

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class CollectView(GenericAPIView, ListModelMixin, CreateModelMixin):
    """收藏会议"""
    serializer_class = CollectSerializer
    queryset = Collect.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_MEETING,
                           OperationLogType.OP_TYPE_COLLECT,
                           OperationLogDesc.OP_DESC_MEETING_COLLECT_CODE) as log_context:
            log_context.log_vars = [request.data.get('meeting')]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        meeting_id = request.data.get('meeting')
        meeting_id = check_int(meeting_id)
        user_id = request.user.id
        if Meeting.objects.filter(id=meeting_id, is_delete=0).count() == 0:
            logger.error('Meeting {} is not exist'.format(meeting_id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        collect_users = Collect.objects.filter(meeting_id=meeting_id, user_id=user_id)
        if collect_users.count() == 0:
            user_collect = Collect.objects.create(meeting_id=meeting_id, user_id=user_id)
            collection_id = user_collect.id
        else:
            collection_id = collect_users.first().id
        resp = ret_access_json(request.user, collection_id=collection_id)
        return resp

    def get_queryset(self):
        queryset = Collect.objects.filter(user_id=self.request.user.id)
        return queryset


class CollectDelView(GenericAPIView, DestroyModelMixin):
    """取消收藏"""
    serializer_class = CollectSerializer
    queryset = Collect.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)

    def delete(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_MEETING,
                           OperationLogType.OP_TYPE_CANCEL_COLLECT,
                           OperationLogDesc.OP_DESC_MEETING_CANCEL_COLLECT_CODE) as log_context:
            log_context.log_vars = [kwargs.get("pk")]
            ret = self.destroy(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def destroy(self, request, *args, **kwargs):
        collection_id = kwargs.get('pk')
        user_id = request.user.id
        if not Collect.objects.filter(id=collection_id, user_id=user_id):
            logger.error('User {} had not collected collection id {}'.format(user_id, collection_id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        super(CollectDelView, self).destroy(request, *args, **kwargs)
        return ret_access_json(request.user)

    def get_queryset(self):
        queryset = Collect.objects.filter(user_id=self.request.user.id)
        return queryset


class MyCollectionsView(GenericAPIView, ListModelMixin):
    """我收藏的会议(列表)"""
    serializer_class = MeetingListSerializer
    queryset = Meeting.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)
    pagination_class = MyPagination

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
            logger.error('Meeting {} does not exist'.format(mid))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
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
    queryset = Activity.objects.filter(is_delete=0, status=2).order_by('-date', 'id')
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)
    pagination_class = MyPagination

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

    def post(self, request, *args, **kwargs):
        policy_version, app_policy_version, cur_date = get_version_params()
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_CREATE,
                           OperationLogDesc.OP_DESC_ACTIVITY_CREATE_CODE) as log_context, \
                PolicyLoggerContext(policy_version, app_policy_version, cur_date) as policy_log_context:
            log_context.log_vars = [request.data.get("title")]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            policy_log_context.result = True
            return ret

    def create(self, request, *args, **kwargs):
        data = check_activity_params(request.data, online, offline)
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
        elif activity_type == online:
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
        return ret_access_json(request.user)


class ActivitiesView(GenericAPIView, ListModelMixin):
    """活动列表"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.filter(is_delete=0, status__gt=2).order_by('-date', 'id')
    filter_backends = [SearchFilter]
    search_fields = ['title']
    pagination_class = MyPagination

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
    pagination_class = MyPagination

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
    pagination_class = MyPagination

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Activity.objects.filter(is_delete=0, status__gt=2, user_id=self.request.user.id).order_by('-date',
                                                                                                             'id')
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
        schedules = request.data.get("schedules")
        check_schedules_string(schedules)
        super(ActivityUpdateView, self).update(request, *args, **kwargs)
        return ret_access_json(request.user)

    def get_queryset(self):
        user_id = self.request.user.id
        queryset = Activity.objects.filter(is_delete=0, status__in=[3, 4], user_id=user_id, id=self.kwargs["pk"])
        if queryset.count() == 0:
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        return queryset


class ActivityPublishView(GenericAPIView, UpdateModelMixin):
    """通过申请"""
    queryset = Activity.objects.filter(is_delete=0, status=2)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_ACTIVITY_PUBLISH_PASS_CODE) as log_context:
            log_context.log_vars = [kwargs.get('pk')]
            ret = self.update(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def update(self, request, *args, **kwargs):
        activity_id = kwargs.get('pk')
        if Activity.objects.filter(id=activity_id, status=2).count() == 0:
            logger.error("Invalid activity id:{}".format(activity_id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        logger.info('activity id: {}'.format(activity_id))
        img_url = gene_wx_code.run(activity_id)
        logger.info('Generate event page QR code: {}'.format(img_url))
        Activity.objects.filter(id=activity_id, status=2).update(status=3, wx_code=img_url)
        logger.info('The activity has been reviewed and published')
        return ret_access_json(request.user)


class ActivityRejectView(GenericAPIView, UpdateModelMixin):
    """驳回申请"""
    queryset = Activity.objects.filter(is_delete=0, status=2)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_ACTIVITY_PUBLISH_REJECT_CODE) as log_context:
            log_context.log_vars = [kwargs.get("pk")]
            ret = self.update(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def update(self, request, *args, **kwargs):
        activity_id = kwargs.get('pk')
        if Activity.objects.filter(id=activity_id, status=2).count() == 0:
            logger.error("Invalid activity id:{}".format(activity_id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        Activity.objects.filter(id=activity_id, status=2).update(status=1)
        return ret_access_json(request.user)


class ActivityDelView(GenericAPIView, UpdateModelMixin):
    """删除一个活动"""
    queryset = Activity.objects.filter(is_delete=0, status__gt=2)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_DELETE,
                           OperationLogDesc.OP_DESC_ACTIVITY_DELETE_CODE) as log_context:
            log_context.log_vars = [kwargs.get('pk')]
            ret = self.update(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def update(self, request, *args, **kwargs):
        activity_id = self.kwargs.get('pk')
        if Activity.objects.filter(id=activity_id, status__gt=2, is_delete=0).count == 0:
            logger.error("Invalid activity id:{}".format(activity_id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        Activity.objects.filter(id=activity_id).update(is_delete=1)
        return ret_access_json(request.user)


class ActivityDraftView(GenericAPIView, CreateModelMixin):
    """创建活动草案"""
    serializer_class = ActivitySerializer
    queryset = Activity.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def post(self, request, *args, **kwargs):
        policy_version, app_policy_version, cur_date = get_version_params()
        with LoggerContext(request, OperationLogModule.OP_MODULE_MEETING,
                           OperationLogType.OP_TYPE_CREATE,
                           OperationLogDesc.OP_DESC_ACTIVITY_CREATE_DRAFT_CODE) as log_context, \
                PolicyLoggerContext(policy_version, app_policy_version, cur_date) as policy_log_context:
            log_context.log_vars = [request.data.get("title")]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            policy_log_context.result = True
            return ret

    def create(self, request, *args, **kwargs):
        data = check_activity_params(request.data, online, offline)
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
        elif activity_type == online:
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
        return ret_access_json(request.user)


class ActivitiesDraftView(GenericAPIView, ListModelMixin):
    """活动草案列表"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)
    pagination_class = MyPagination

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
        super(SponsorActivityDraftView, self).destroy(request, *args, **kwargs)
        return ret_access_json(request.user)

    def get_queryset(self):
        queryset = Activity.objects.filter(is_delete=0, status=1, user_id=self.request.user.id).order_by('-date', 'id')
        return queryset


class DraftUpdateView(GenericAPIView, UpdateModelMixin):
    """修改活动草案"""
    serializer_class = ActivityDraftUpdateSerializer
    queryset = Activity.objects.filter(is_delete=0, status=1)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_ACTIVITY_MODIFY_DRAFT_CODE) as log_context:
            log_context.log_vars = [kwargs.get('pk')]
            ret = self.update(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def update(self, request, *args, **kwargs):
        activity_id = self.kwargs.get('pk')
        user_id = self.request.user.id
        if not Activity.objects.filter(id=activity_id, user_id=user_id, status=1):
            logger.error('Invalid activity id:{}'.format(str(activity_id)))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        data = check_activity_params(request.data, online, offline)
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
        elif activity_type == online:
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
        return ret_access_json(request.user)


class DraftPublishView(GenericAPIView, UpdateModelMixin):
    """修改活动草案并申请发布"""
    serializer_class = ActivityDraftUpdateSerializer
    queryset = Activity.objects.filter(is_delete=0, status=1)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_ACTIVITY_PUBLISH_DRAFT_CODE) as log_context:
            log_context.log_vars = [kwargs.get('pk')]
            ret = self.update(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def update(self, request, *args, **kwargs):
        activity_id = self.kwargs.get('pk')
        user_id = self.request.user.id
        if not Activity.objects.filter(id=activity_id, user_id=user_id, status=1):
            logger.error('Invalid activity id {}'.format(str(activity_id)))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        data = check_activity_params(request.data, online, offline)
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
        elif activity_type == online:
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
        return ret_access_json(request.user)


class SponsorActivitiesPublishingView(GenericAPIView, ListModelMixin):
    """发布中的活动"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)
    pagination_class = MyPagination

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

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_COLLECT,
                           OperationLogDesc.OP_DESC_ACTIVITY_COLLECT_CODE) as log_context:
            log_context.log_vars = [request.data.get('activity')]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        activity_id = request.data.get('activity')
        activity_id = check_int(activity_id)
        user_id = request.user.id
        if not Activity.objects.filter(id=activity_id, status__in=[3, 4, 5], is_delete=0):
            logger.error('Activity {} is not exist'.format(activity_id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        if ActivityCollect.objects.filter(activity_id=activity_id, user_id=user_id).count() == 0:
            ActivityCollect.objects.create(activity_id=activity_id, user_id=user_id)
        return ret_access_json(request.user)


class ActivityCollectDelView(GenericAPIView, DestroyModelMixin):
    """取消收藏活动"""
    serializer_class = ActivityCollectSerializer
    queryset = ActivityCollect.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)

    def delete(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_CANCEL_COLLECT,
                           OperationLogDesc.OP_DESC_ACTIVITY_CANCEL_COLLECT_CODE) as log_context:
            log_context.log_vars = [kwargs.get('pk')]
            ret = self.destroy(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def destroy(self, request, *args, **kwargs):
        user_id = request.user.id
        collection_id = kwargs.get('pk')
        if not ActivityCollect.objects.filter(id=collection_id, user_id=user_id):
            logger.error('User {} had not collected collection id {}'.format(user_id, collection_id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        super(ActivityCollectDelView, self).destroy(request, *args, **kwargs)
        return ret_access_json(request.user)

    def get_queryset(self):
        queryset = ActivityCollect.objects.filter(user_id=self.request.user.id, id=self.kwargs['pk'])
        return queryset


class MyActivityCollectionsView(GenericAPIView, ListModelMixin):
    """我收藏的活动(列表)"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (CustomAuthentication,)
    pagination_class = MyPagination

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


class MeetingActivityDateView(GenericAPIView, ListModelMixin):
    _meeting_queryset = Meeting.objects.filter(is_delete=0)
    _activity_queryset = Activity.objects.filter(status__in=[3, 4, 5], is_delete=0)

    def get_meetings(self):
        date_list = self._meeting_queryset.filter(
            date__gte=(datetime.datetime.now() - datetime.timedelta(days=180)).strftime('%Y-%m-%d'),
            date__lte=(datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')). \
            distinct().order_by('-date', 'id').values_list("date", flat=True)
        return date_list

    def get_activity(self):
        date_list = self._activity_queryset.filter(
            date__gte=(datetime.datetime.now() - datetime.timedelta(days=180)).strftime('%Y-%m-%d'),
            date__lte=(datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')). \
            distinct().order_by('-date', 'id').values_list("date", flat=True)
        return date_list

    def get(self, request, *args, **kwargs):
        query_type_str = request.GET.get("type")
        check_type(query_type_str)
        ret_list = list()
        if query_type_str == "all":
            meetings = self.get_meetings()
            ret_list.extend(meetings)
            activity = self.get_activity()
            ret_list.extend(activity)
        elif query_type_str == "meetings":
            meetings = self.get_meetings()
            ret_list.extend(meetings)
        elif query_type_str == "activity":
            activity = self.get_activity()
            ret_list.extend(activity)
        all_date = sorted(list(set(ret_list)))
        return ret_json(data=all_date)


class MeetingActivityDataView(GenericAPIView, ListModelMixin):
    _meeting_queryset = Meeting.objects.filter(is_delete=0)
    _activity_queryset = Activity.objects.filter(status__in=[3, 4, 5], is_delete=0)

    def get_meetings(self, query_date):
        queryset = self._meeting_queryset.filter(date=query_date).order_by('-date', 'id').values()
        records = Record.objects.filter(platform="bilibili", url__isnull=False).values()
        record_dict = dict()
        for record in records:
            if record['platform'] == 'bilibili' and record['url']:
                record_dict[record['mid']] = record['url']
        list_data = [{
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
        } for meeting in queryset]
        return list_data

    def get_activity(self, query_date):
        queryset = self._activity_queryset.filter(date=query_date).order_by('-date', 'id').values()
        list_data = [{
            'id': activity["id"],
            'title': activity["title"],
            'start_date': activity["date"],
            'end_date': activity["date"],
            'activity_type': activity["activity_type"],
            'address': activity["address"],
            'detail_address': activity["detail_address"],
            'longitude': activity["longitude"],
            'latitude': activity["latitude"],
            'synopsis': activity["synopsis"],
            'sign_url': activity["sign_url"],
            'replay_url': activity["replay_url"],
            'register_url': activity["register_url"],
            'poster': activity["poster"],
            'wx_code': activity["wx_code"],
            'schedules': json.loads(activity["schedules"])
        } for activity in queryset]
        return list_data

    def get(self, request, *args, **kwargs):
        query_date_str = request.GET.get("date")
        query_type_str = request.GET.get("type")
        check_date(query_date_str)
        check_type(query_type_str)
        ret_list = list()
        if query_type_str == "all":
            meetings = self.get_meetings(query_date_str)
            ret_list.extend(meetings)
            activity = self.get_activity(query_date_str)
            ret_list.extend(activity)
        elif query_type_str == "meetings":
            meetings = self.get_meetings(query_date_str)
            ret_list.extend(meetings)
        elif query_type_str == "activity":
            activity = self.get_activity(query_date_str)
            ret_list.extend(activity)
        ret_dict = {
            'date': query_date_str,
            'timeData': ret_list
        }
        return ret_json(data=ret_dict)
