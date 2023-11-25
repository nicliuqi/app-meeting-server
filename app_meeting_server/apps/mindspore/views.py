import datetime
import math
import secrets
from django.conf import settings

from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from rest_framework import permissions
from rest_framework.filters import SearchFilter
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin, ListModelMixin, RetrieveModelMixin, \
    DestroyModelMixin
from rest_framework_simplejwt.views import TokenRefreshView

from app_meeting_server.utils import wx_apis
from app_meeting_server.utils.my_pagination import MyPagination
from app_meeting_server.utils.permissions import MeetigsAdminPermission, ActivityAdminPermission, \
    QueryPermission, MaintainerPermission, SponsorPermission, MaintainerAndAdminPermission, AdminPermission
from mindspore.models import Activity, ActivityCollect, Record
from mindspore.models import GroupUser, Group, User, Collect, City, CityUser
from mindspore.serializers import LoginSerializer, GroupsSerializer, GroupUserAddSerializer, GroupUserDelSerializer, \
    UserInfoSerializer, UserGroupSerializer, \
    MeetingSerializer, MeetingDelSerializer, MeetingsListSerializer, CollectSerializer, CitiesSerializer, \
    CityUserAddSerializer, CityUserDelSerializer, UserCitySerializer, SponsorSerializer, ActivitySerializer, \
    ActivityUpdateSerializer, ActivityDraftUpdateSerializer, ActivitiesSerializer, ActivityRetrieveSerializer, \
    ActivityCollectSerializer, UpdateUserInfoSerializer, UsersSerializer
from mindspore.utils.send_email import sendmail
from mindspore.utils.tencent_apis import *
from mindspore.utils import gene_wx_code, drivers, send_cancel_email
from app_meeting_server.utils.auth import CustomAuthentication
from app_meeting_server.utils.common import get_cur_date, decrypt_openid, \
    refresh_token_and_refresh_token, clear_token, get_anonymous_openid, start_thread, get_date_by_start_and_end
from app_meeting_server.utils.operation_log import LoggerContext, OperationLogModule, OperationLogDesc, \
    OperationLogType, PolicyLoggerContext
from app_meeting_server.utils.ret_api import MyValidationError, ret_access_json, ret_json
from app_meeting_server.utils.check_params import check_group_id_and_user_ids, \
    check_user_ids, check_activity_more_params, check_refresh_token, check_meetings_more_params, \
    check_publish, check_type, check_date, check_int, check_schedules_more_string
from app_meeting_server.utils.ret_code import RetCode

logger = logging.getLogger('log')


# ------------------------------common view------------------------------
class PingView(GenericAPIView):
    """心跳"""

    def get(self, request, *args):
        return ret_json(code=200, msg='the status is ok')


# ------------------------------user view------------------------------
class LoginView(GenericAPIView, CreateModelMixin, ListModelMixin):
    """用户注册与授权登陆"""
    serializer_class = LoginSerializer
    queryset = User.objects.all()

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_LOGIN,
                           OperationLogDesc.OP_DESC_USER_LOGIN_CODE) as log_context:
            log_context.log_vars = ["anonymous"]
            ret = self.create(request, *args, **kwargs)
            log_context.request.user = User.objects.filter(id=ret.data.get("user_id")).first()
            log_context.log_vars = [str(ret.data.get("user_id"))]
            log_context.result = ret
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
    authentication_classes = (CustomAuthentication,)
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
        policy_version = settings.PRIVACY_POLICY_VERSION
        app_policy_version = settings.PRIVACY_APP_POLICY_VERSION
        cur_date = get_cur_date()
        with PolicyLoggerContext(policy_version, app_policy_version, cur_date, result=False) as policy_log_context:
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
    authentication_classes = (CustomAuthentication,)
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
        anonymous_name = settings.ANONYMOUS_NAME
        user_id = request.user.id
        with PolicyLoggerContext(policy_version, app_policy_version, cur_date, result=False,
                                 is_agreen=False) as policy_log_context:
            if request.user.level == MeetigsAdminPermission.level or \
                    request.user.activity_level == ActivityAdminPermission.activity_level:
                raise MyValidationError(RetCode.STATUS_START_POLICY_ONLY_ONE_ADMIN)
            anonymous_openid = get_anonymous_openid()
            with transaction.atomic():
                User.objects.filter(id=user_id).update(revoke_agreement_time=cur_date,
                                                       openid=anonymous_openid,
                                                       gitee_name=anonymous_name,
                                                       nickname=anonymous_name)
                Meeting.objects.filter(user__id=user_id).update(emaillist=None)
                policy_log_context.result = True
        clear_token(request.user)
        resp = ret_json(msg="Revoke agreement of privacy policy")
        return resp


class UpdateUserInfoView(GenericAPIView, UpdateModelMixin):
    """修改用户信息"""
    serializer_class = UpdateUserInfoSerializer
    queryset = User.objects.filter(is_delete=0).exclude(nickname=settings.ANONYMOUS_NAME)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (AdminPermission,)

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_USER_MODIFY_CODE) as log_context:
            log_context.log_vars = [request.user.id, request.user.id]
            ret = self.update(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def update(self, request, *args, **kwargs):
        super(UpdateUserInfoView, self).update(request, *args, **kwargs)
        return ret_access_json(request.user)


class UserInfoView(GenericAPIView, RetrieveModelMixin):
    """查询用户信息"""
    serializer_class = UserInfoSerializer
    queryset = User.objects.filter(is_delete=0).exclude(nickname=settings.ANONYMOUS_NAME)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        user_id = kwargs.get('pk')
        if user_id != request.user.id:
            logger.warning('user_id did not match.user_id:{}, request.user.id:{}'.format(user_id, request.user.id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        return self.retrieve(request, *args, **kwargs)


class UsersIncludeView(GenericAPIView, ListModelMixin):
    """sig组成员列表"""
    serializer_class = UsersSerializer
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
        user = User.objects.filter(id__in=ids, is_delete=0). \
            exclude(nickname=settings.ANONYMOUS_NAME).order_by('nickname')
        return user


class UsersExcludeView(GenericAPIView, ListModelMixin):
    """非sig组成员列表"""
    serializer_class = UsersSerializer
    queryset = User.objects.all()
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
        user = User.objects.filter(is_delete=0). \
            exclude(nickname=settings.ANONYMOUS_NAME). \
            exclude(id__in=ids).order_by('nickname')
        return user


class SigsView(GenericAPIView, ListModelMixin):
    """SIG列表"""
    serializer_class = GroupsSerializer
    queryset = Group.objects.filter(group_type=1).order_by("name")
    filter_backends = [SearchFilter]
    search_fields = ['name']
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MeetigsAdminPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class UserGroupView(GenericAPIView, ListModelMixin):
    """查询用户所在SIG组信息"""
    serializer_class = UserGroupSerializer
    queryset = GroupUser.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MaintainerPermission,)

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
        count_user = User.objects.filter(id__in=new_list_ids).filter(is_delete=0).exclude(
            nickname=settings.ANONYMOUS_NAME).count()
        if count_user != len(new_list_ids):
            logger.info("GroupUserDelView find anonymous or be deleted")
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        GroupUser.objects.filter(group_id=new_group_id, user_id__in=new_list_ids).delete()
        return ret_access_json(request.user)


class GroupsView(GenericAPIView, ListModelMixin):
    """组信息"""
    serializer_class = GroupsSerializer
    queryset = Group.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MeetigsAdminPermission,)

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
    serializer_class = UsersSerializer
    queryset = User.objects.filter(is_delete=0).exclude(nickname=settings.ANONYMOUS_NAME)
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    permission_classes = (MeetigsAdminPermission,)
    authentication_classes = (CustomAuthentication,)
    pagination_class = MyPagination

    def get(self, request, *args, **kwargs):
        city_id = self.request.GET.get('city')
        city_id = check_int(city_id)
        if not City.objects.filter(id=city_id):
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        city_id = self.request.GET.get('city')
        city_users = CityUser.objects.filter(city_id=city_id).values_list("user_id", flat=True)
        user = User.objects.filter(id__in=city_users, is_delete=0).exclude(nickname=settings.ANONYMOUS_NAME)
        return user


class NonCityMembersView(GenericAPIView, ListModelMixin):
    """非城市组成员列表"""
    serializer_class = UsersSerializer
    queryset = User.objects.filter(is_delete=0).exclude(nickname=settings.ANONYMOUS_NAME)
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MeetigsAdminPermission,)
    pagination_class = MyPagination

    def get(self, request, *args, **kwargs):
        city_id = self.request.GET.get('city')
        city_id = check_int(city_id)
        if not City.objects.filter(id=city_id):
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        city_id = self.request.GET.get('city')
        city_users = CityUser.objects.filter(city_id=city_id).values_list("user_id", flat=True)
        user = User.objects.filter(is_delete=0).exclude(id__in=city_users)
        return user


class SponsorsView(GenericAPIView, ListModelMixin):
    """活动发起人列表"""
    serializer_class = SponsorSerializer
    queryset = User.objects.filter(activity_level=2, is_delete=0).exclude(nickname=settings.ANONYMOUS_NAME)
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)
    pagination_class = MyPagination

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class NonSponsorsView(GenericAPIView, ListModelMixin):
    """非活动发起人列表"""
    serializer_class = SponsorSerializer
    queryset = User.objects.filter(activity_level=1, is_delete=0).exclude(nickname=settings.ANONYMOUS_NAME)
    filter_backends = [SearchFilter]
    search_fields = ['nickname']
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)
    pagination_class = MyPagination

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class SponsorsAddView(GenericAPIView, CreateModelMixin):
    """批量添加活动发起人"""
    queryset = User.objects.filter(is_delete=0).exclude(nickname=settings.ANONYMOUS_NAME)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

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
        user_ids = request.data.get('ids')
        new_user_ids = check_user_ids(user_ids)
        match_queryset = User.objects.filter(id__in=new_user_ids, activity_level=1, is_delete=0). \
            exclude(nickname=settings.ANONYMOUS_NAME).count()
        if len(new_user_ids) != match_queryset:
            logger.error("The input ids: {}, parse result {} not eq query result {}".format(user_ids, new_user_ids,
                                                                                            match_queryset))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        User.objects.filter(id__in=new_user_ids, activity_level=1, is_delete=0).update(activity_level=2)
        return ret_access_json(request.user)


class SponsorsDelView(GenericAPIView, CreateModelMixin):
    """批量删除活动发起人"""
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
        match_queryset = User.objects.filter(id__in=new_user_ids, activity_level=2). \
            exclude(nickname=settings.ANONYMOUS_NAME).count()
        if match_queryset != len(new_user_ids):
            logger.error("The input ids: {}, parse result {} not eq query result {}".format(user_ids, new_user_ids,
                                                                                            match_queryset))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        User.objects.filter(id__in=new_user_ids, activity_level=2).update(activity_level=1)
        return ret_access_json(request.user)


class CitiesView(GenericAPIView, ListModelMixin):
    """城市列表"""
    serializer_class = CitiesSerializer
    queryset = City.objects.all().order_by("name")
    filter_backends = [SearchFilter]
    search_fields = ['name']
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MaintainerAndAdminPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class AddCityView(GenericAPIView, CreateModelMixin):
    """添加城市"""
    serializer_class = CitiesSerializer
    queryset = City.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MeetigsAdminPermission,)

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
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
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        etherpad = '{}/p/meetings-MSG/{}'.format(settings.ETHERPAD_PREFIX, name)
        City.objects.create(name=name, etherpad=etherpad)
        return ret_access_json(request.user)


class CityUserAddView(GenericAPIView, CreateModelMixin):
    """批量新增城市组成员"""
    serializer_class = CityUserAddSerializer
    queryset = GroupUser.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MeetigsAdminPermission,)

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_MODIFY,
                           OperationLogDesc.OP_DESC_CITY_ADD_USER_CODE) as log_context:
            log_context.log_vars = [request.data.get("city_id"), request.data.get("ids")]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        super(CityUserAddView, self).create(request, *args, **kwargs)
        return ret_access_json(request.user)


class CityUserDelView(GenericAPIView, CreateModelMixin):
    """批量删除城市组组成员"""
    serializer_class = CityUserDelSerializer
    queryset = GroupUser.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MeetigsAdminPermission,)

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_USER,
                           OperationLogType.OP_TYPE_DELETE,
                           OperationLogDesc.OP_DESC_CITY_REMOVE_USER_CODE) as log_context:
            log_context.log_vars = [request.data.get("city_id"), request.data.get("ids")]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        super(CityUserDelView, self).create(request, *args, **kwargs)
        return ret_access_json(request.user)


class UserCityView(GenericAPIView, ListModelMixin):
    """查询用户所在城市组"""
    serializer_class = UserCitySerializer
    queryset = CityUser.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MaintainerPermission,)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        try:
            usercity = CityUser.objects.filter(user_id=self.kwargs['pk']).all()
            return usercity
        except KeyError:
            pass


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
        collected_meetings_count = Meeting.objects.filter(is_delete=0, id__in=(
            Collect.objects.filter(user_id=user_id).values_list('meeting_id', flat=True))).count()
        collected_activities_count = Activity.objects.filter(is_delete=0, id__in=(
            ActivityCollect.objects.filter(user_id=user_id).values_list('activity_id', flat=True))).count()
        res = {'collected_meetings_count': collected_meetings_count,
               'collected_activities_count': collected_activities_count}
        # permission limited
        if level == 2:
            created_meetings_count = Meeting.objects.filter(is_delete=0, user_id=user_id).count()
            res['created_meetings_count'] = created_meetings_count
        if level == 3:
            created_meetings_count = Meeting.objects.filter(is_delete=0).count()
            res['created_meetings_count'] = created_meetings_count
        if activity_level == 2:
            published_activities_count = Activity.objects.filter(is_delete=0, status__gt=2, user_id=user_id).count()
            drafts_count = Activity.objects.filter(is_delete=0, status=1, user_id=user_id).count()
            publishing_activities_count = Activity.objects.filter(is_delete=0, status=2, user_id=user_id).count()
            res['published_activities_count'] = published_activities_count
            res['drafts_count'] = drafts_count
            res['publishing_activities_count'] = publishing_activities_count
        if activity_level == 3:
            published_activities_count = Activity.objects.filter(is_delete=0, status__gt=2).count()
            drafts_count = Activity.objects.filter(is_delete=0, status=1, user_id=user_id).count()
            publishing_activities_count = Activity.objects.filter(is_delete=0, status=2).count()
            res['published_activities_count'] = published_activities_count
            res['drafts_count'] = drafts_count
            res['publishing_activities_count'] = publishing_activities_count
        return JsonResponse(res)


# ------------------------------meeting view------------------------------
# noinspection PyUnresolvedReferences
class CreateMeetingView(GenericAPIView, CreateModelMixin):
    """预定会议"""
    serializer_class = MeetingSerializer
    queryset = Meeting.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MaintainerPermission,)

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_MEETING,
                           OperationLogType.OP_TYPE_CREATE,
                           OperationLogDesc.OP_DESC_MEETING_CREATE_CODE) as log_context:
            log_context.log_vars = [request.data.get('topic')]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        data = check_meetings_more_params(request, Group, City)
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
        emaillist = data.get('emaillist', '')
        agenda = data.get('agenda')
        record = data.get('record')
        group_id = data.get('group_id')
        user_id = request.user.id

        # 1.查询待创建的会议与现有的预定会议是否冲突
        start_search = datetime.datetime.strftime(
            (datetime.datetime.strptime(start, '%H:%M') - datetime.timedelta(minutes=30)),
            '%H:%M')
        end_search = datetime.datetime.strftime(
            (datetime.datetime.strptime(end, '%H:%M') + datetime.timedelta(minutes=30)),
            '%H:%M')
        meetings = Meeting.objects.filter(is_delete=0, date=date, end__gt=start_search, start__lt=end_search).values()
        unavailable_host_ids = [meeting['host_id'] for meeting in meetings]
        available_host_id = list(set(host_list) - set(unavailable_host_ids))
        if len(available_host_id) == 0:
            logger.info('no available host')
            raise MyValidationError(RetCode.STATUS_MEETING_DATE_CONFLICT)
        # 2.从available_host_id中随机生成一个host_id,并在host_dict中取出
        host_id = secrets.choice(available_host_id)
        logger.info('host_id: {}'.format(host_id))
        status, resp = drivers.createMeeting(platform, date, start, end, topic, host_id, record)
        if status not in [200, 201]:
            logger.error("Failed to create meeting, and code is {}".format(str(status)))
            raise MyValidationError(RetCode.STATUS_MEETING_FAILED_CREATE)
        meeting_id = resp.get("mmid")
        meeting_code = resp.get('mid')
        join_url = resp.get('join_url')
        # 3.保存数据
        new_meetings = Meeting.objects.create(
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
        logger.info('created a {} meeting which mid is {}.'.format(platform, meeting_code))
        start_thread(sendmail, meeting_code, record)
        return ret_access_json(request.user, id=new_meetings.id)


class CancelMeetingView(GenericAPIView, UpdateModelMixin):
    """取消会议"""
    serializer_class = MeetingDelSerializer
    queryset = Meeting.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (MaintainerAndAdminPermission,)

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_MEETING,
                           OperationLogType.OP_TYPE_DELETE,
                           OperationLogDesc.OP_DESC_MEETING_DELETE_CODE) as log_context:
            log_context.log_vars = [kwargs.get('mid')]
            ret = self.update(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def update(self, request, *args, **kwargs):
        user_id = request.user.id
        mid = self.kwargs.get('mid')
        if Meeting.objects.filter(mid=mid, is_delete=0).count() == 0:
            logger.error('Invalid meeting id:{}'.format(mid))
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

        status = drivers.cancelMeeting(mid)
        # 数据库更改Meeting的is_delete=1
        if status != 200:
            logger.error('Failed to delete meeting {}'.format(str(status)))
            raise MyValidationError(RetCode.STATUS_FAILED)
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
        logger.info('{} has canceled the meeting which mid was {}'.format(self.request.user.gitee_name, mid))
        return ret_access_json(request.user)


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
    filter_backends = [SearchFilter]
    search_fields = ['topic']
    pagination_class = MyPagination

    def get(self, request, *args, **kwargs):
        today = datetime.datetime.strftime(datetime.datetime.today(), '%Y-%m-%d')
        meeting_range = self.request.GET.get('range')
        meeting_type = self.request.GET.get('type')
        if meeting_type == 'sig':
            self.queryset = self.queryset.filter(meeting_type=1)
        if meeting_type == 'msg':
            self.queryset = self.queryset.filter(meeting_type=2)
        if meeting_type == 'tech':
            self.queryset = self.queryset.filter(meeting_type=3)
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
        with LoggerContext(request, OperationLogModule.OP_MODULE_MEETING,
                           OperationLogType.OP_TYPE_COLLECT,
                           OperationLogDesc.OP_DESC_MEETING_COLLECT_CODE) as log_context:
            log_context.log_vars = [request.data.get('meeting')]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        meeting_id = request.data.get('meeting')
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


class CollectionDelView(GenericAPIView, DestroyModelMixin):
    """取消收藏会议"""
    serializer_class = CollectSerializer
    queryset = Collect.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def delete(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_MEETING,
                           OperationLogType.OP_TYPE_CANCEL_COLLECT,
                           OperationLogDesc.OP_DESC_MEETING_CANCEL_COLLECT_CODE) as log_context:
            log_context.log_vars = [kwargs.get('pk')]
            ret = self.destroy(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def destroy(self, request, *args, **kwargs):
        user_id = request.user.id
        collection_id = kwargs.get('pk')
        if not Collect.objects.filter(id=collection_id, user_id=user_id):
            logger.error('User {} had not collected collection id {}'.format(user_id, collection_id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        super(CollectionDelView, self).destroy(request, *args, **kwargs)
        return ret_access_json(request.user)

    def get_queryset(self):
        queryset = Collect.objects.filter(user_id=self.request.user.id)
        return queryset


class MyMeetingsView(GenericAPIView, ListModelMixin):
    """我预定的所有会议"""
    serializer_class = MeetingsListSerializer
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


class MyCollectionsView(GenericAPIView, ListModelMixin):
    """我收藏的会议"""
    serializer_class = MeetingsListSerializer
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


# ------------------------------activity view------------------------------


class ActivityCreateView(GenericAPIView, CreateModelMixin):
    """创建活动并申请发布"""
    serializer_class = ActivitySerializer
    queryset = Activity.objects.all()
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)

    def post(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_CREATE,
                           OperationLogDesc.OP_DESC_ACTIVITY_CREATE_CODE) as log_context:
            log_context.log_vars = [request.data.get("title")]
            ret = self.create(request, *args, **kwargs)
            log_context.result = ret
            return ret

    def create(self, request, *args, **kwargs):
        data = check_activity_more_params(request.data)
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
        poster = data.get('poster')
        user_id = request.user.id
        publish = request.GET.get('publish')
        publish = check_publish(publish)
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
                schedules=schedules,
                poster=poster,
                status=2,
                user_id=user_id
            )
        else:
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
                schedules=schedules,
                poster=poster,
                user_id=user_id,
            )
        return ret_access_json(request.user)


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
        schedules = request.data.get("schedules")
        replay_url = request.data.get("replay_url")
        check_schedules_more_string(schedules)
        if not replay_url.startswith('https://'):
            logger.error('Invalid replay_url url: {}'.format(replay_url))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        super(ActivityUpdateView, self).update(request, *args, **kwargs)
        return ret_access_json(request.user)

    def get_queryset(self):
        user_id = self.request.user.id
        activity_level = User.objects.get(id=user_id).activity_level
        queryset = Activity.objects.filter(is_delete=0, status__in=[3, 4, 5], user_id=user_id)
        if activity_level == 3:
            queryset = Activity.objects.filter(is_delete=0, status__in=[3, 4, 5])
        return queryset


class WaitingActivities(GenericAPIView, ListModelMixin):
    """待审活动列表"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.filter(is_delete=0, status=2)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)
    pagination_class = MyPagination

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class WaitingActivity(GenericAPIView, RetrieveModelMixin):
    """待审活动详情"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.filter(is_delete=0, status=2)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class ApproveActivityView(GenericAPIView, UpdateModelMixin):
    """通过审核"""
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


class DenyActivityView(GenericAPIView, UpdateModelMixin):
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


class ActivityDeleteView(GenericAPIView, UpdateModelMixin):
    """删除活动"""
    queryset = Activity.objects.filter(is_delete=0, status__gt=2)
    authentication_classes = (CustomAuthentication,)
    permission_classes = (ActivityAdminPermission,)

    def put(self, request, *args, **kwargs):
        with LoggerContext(request, OperationLogModule.OP_MODULE_ACTIVITY,
                           OperationLogType.OP_TYPE_DELETE,
                           OperationLogDesc.OP_DESC_ACTIVITY_DELETE_CODE) as log_context:
            log_context.log_vars = [kwargs.get("pk")]
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
        user_id = request.user.id
        activity_id = self.kwargs.get('pk')
        if Activity.objects.filter(id=activity_id, user_id=user_id, status=1):
            logger.error('Invalid activity id: {}'.format(activity_id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        data = check_activity_more_params(request.data)
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
        poster = data.get('poster')
        publish = self.request.GET.get('publish')
        publish = check_publish(publish)
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
                schedules=schedules,
                poster=poster,
                status=2
            )
        else:
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
                schedules=schedules,
                poster=poster,
            )
        return ret_access_json(request.user)


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
        super(DraftView, self).destroy(request, *args, **kwargs)
        return ret_access_json(request.user)

    def get_queryset(self):
        queryset = Activity.objects.filter(is_delete=0, status=1, user_id=self.request.user.id).order_by('-start_date',
                                                                                                         'id')
        return queryset


class ActivitiesListView(GenericAPIView, ListModelMixin):
    """活动列表"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.filter(is_delete=0, status__gt=2).order_by('-start_date', 'id')
    pagination_class = MyPagination

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
    pagination_class = MyPagination

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
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)
    pagination_class = MyPagination

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Activity.objects.filter(is_delete=0, status=1, user_id=self.request.user.id).order_by('-start_date',
                                                                                                         'id')
        return queryset


class PublishedActivitiesView(GenericAPIView, ListModelMixin):
    """我发布的活动列表(已发布)"""
    serializer_class = ActivitiesSerializer
    queryset = Activity.objects.all().order_by('-start_date', 'id')
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)
    pagination_class = MyPagination

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
    authentication_classes = (CustomAuthentication,)
    permission_classes = (SponsorPermission,)
    pagination_class = MyPagination

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Activity.objects.filter(is_delete=0, status=2, user_id=self.request.user.id).order_by('-start_date',
                                                                                                         'id')
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
        user_id = request.user.id
        if not isinstance(activity_id, int):
            logger.error('Invalid activity id: {}'.format(activity_id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        if not Activity.objects.filter(id=activity_id, status__in=[3, 4, 5], is_delete=0):
            logger.error('Activity {} is not exist'.format(activity_id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        if ActivityCollect.objects.filter(activity_id=activity_id, user_id=user_id).count() == 0:
            ActivityCollect.objects.create(activity_id=activity_id, user_id=user_id)
        return ret_access_json(request.user)


class ActivityCollectionsView(GenericAPIView, ListModelMixin):
    """收藏活动列表"""
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
        queryset = Activity.objects.filter(is_delete=0, id__in=collection_lst).order_by('-start_date', 'id')
        return queryset


class ActivityCollectionDelView(GenericAPIView, DestroyModelMixin):
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
        super(ActivityCollectionDelView, self).destroy(request, *args, **kwargs)
        return ret_access_json(request.user)

    def get_queryset(self):
        queryset = ActivityCollect.objects.filter(user_id=self.request.user.id, id=self.kwargs["pk"])
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
        all_date_list = self._activity_queryset.filter(
            start_date__gte=(datetime.datetime.now() - datetime.timedelta(days=180)).strftime('%Y-%m-%d'),
            start_date__lte=(datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')).values(
            "start_date", "end_date")
        all_ret_date_list = list()
        for all_date in all_date_list:
            start_date_str = all_date["start_date"]
            end_date_str = all_date["end_date"]
            temp = get_date_by_start_and_end(start_date_str, end_date_str)
            all_ret_date_list.extend(temp)
        return all_ret_date_list

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
        queryset = self._meeting_queryset.filter(date=query_date).values().order_by('-date', 'id')
        list_data = [{
            'id': meeting["id"],
            'group_name': meeting["group_name"],
            'meeting_type': meeting["meeting_type"],
            'city': meeting["city"],
            'startTime': meeting["start"],
            'endTime': meeting["end"],
            'duration': math.ceil(float(meeting["end"].replace(':', '.'))) - math.floor(
                float(meeting["start"].replace(':', '.'))),
            'duration_time': meeting["start"].split(':')[0] + ':00' + '-' + str(
                math.ceil(float(meeting["end"].replace(':', '.')))) + ':00',
            'name': meeting["topic"],
            'creator': meeting["sponsor"],
            'detail': meeting["agenda"],
            'url': User.objects.get(id=meeting["user_id"]).avatar,
            'join_url': meeting["join_url"],
            'meeting_id': meeting["mid"],
            'etherpad': meeting["etherpad"],
            'replay_url': meeting["replay_url"],
            'platform': meeting["mplatform"]
        } for meeting in queryset]
        return list_data

    def get_activity(self, query_date):
        queryset = self._activity_queryset.filter(start_date__lte=query_date, end_date__gte=query_date).values().order_by('create_time')
        list_data = [{
            'id': activity["id"],
            'title': activity["title"],
            'start_date': activity["start_date"],
            'end_date': activity["end_date"],
            'activity_type': activity["activity_type"],
            'activity_category': activity["activity_category"],
            'address': activity["address"],
            'detail_address': activity["detail_address"],
            'longitude': activity["longitude"],
            'latitude': activity["latitude"],
            'register_method': activity["register_method"],
            'online_url': activity["online_url"],
            'register_url': activity["register_url"],
            'synopsis': activity["synopsis"],
            'sign_url': activity["sign_url"],
            'replay_url': activity["replay_url"],
            'poster': activity["poster"],
            'wx_code': activity["wx_code"],
            'schedules': activity["schedules"]
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
