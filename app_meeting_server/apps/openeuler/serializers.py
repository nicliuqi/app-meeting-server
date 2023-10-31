import logging
import traceback
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from app_meeting_server.utils.check_params import check_group_id, check_user_ids
from app_meeting_server.utils.common import get_uuid, make_signature, encrypt_openid
from app_meeting_server.utils.ret_code import RetCode
from app_meeting_server.utils.wx_apis import get_openid
from app_meeting_server.utils.ret_api import MyValidationError
from openeuler.models import Collect, Group, User, Meeting, GroupUser, Record, Activity, ActivityCollect
from django.db import transaction

logger = logging.getLogger('log')


class GroupUserAddSerializer(ModelSerializer):
    ids = serializers.CharField(max_length=255, write_only=True)
    group_id = serializers.CharField(max_length=255, write_only=True)

    class Meta:
        model = GroupUser
        fields = ['group_id', 'ids']

    def validate_group_id(self, value):
        return check_group_id(Group, value)

    def validate_ids(self, value):
        return check_user_ids(value)

    def create(self, validated_data):
        users = User.objects.filter(id__in=validated_data['ids'], is_delete=0)
        group_id = Group.objects.filter(id=validated_data['group_id']).first()
        try:
            result_list = list()
            for user in users:
                with transaction.atomic():
                    groupuser = GroupUser.objects.create(group_id=group_id.id, user_id=int(user.id))
                    User.objects.filter(id=int(user.id), level=1).update(level=2)
                    result_list.append(groupuser)
            return result_list
        except Exception as e:
            msg = 'Failed to add maintainers to the group'
            logger.error("msg:{}, err:{}".format(msg, e))
            raise MyValidationError(RetCode.INTERNAL_ERROR)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['code'] = 201
        data['msg'] = 'Success to add maintainers to the group'
        return data


class GroupUserDelSerializer(ModelSerializer):
    ids = serializers.CharField(max_length=255, write_only=True)
    group_id = serializers.CharField(max_length=255, write_only=True)

    class Meta:
        model = GroupUser
        fields = ['group_id', 'ids']

    def validate_group_id(self, value):
        return check_group_id(Group, value)

    def validate_ids(self, value):
        return check_user_ids(value)


class GroupsSerializer(ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'group_name']


class GroupSerializer(ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'


class UsersSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'nickname', 'gitee_name', 'avatar']


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'gitee_name']


class MeetingSerializer(ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['id', 'topic', 'sponsor', 'group_name', 'date', 'start', 'end', 'etherpad', 'agenda', 'emaillist',
                  'user_id', 'group_id']
        extra_kwargs = {
            'mid': {'read_only': True},
            'join_url': {'read_only': True},
            'group_name': {'required': True}
        }


class MeetingListSerializer(ModelSerializer):
    collection_id = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = ['id', 'collection_id', 'user_id', 'group_id', 'topic', 'sponsor', 'group_name', 'date', 'start',
                  'end', 'agenda', 'etherpad', 'mid', 'join_url', 'video_url', 'mplatform']

    def get_collection_id(self, obj):
        user = None
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        try:
            return Collect.objects.filter(user_id=user.id, meeting_id=obj.id).values()[0]['id']
        except IndexError:
            return

    def get_video_url(self, obj):
        video_url = Record.objects.filter(mid=obj.mid, platform='bilibili').values()[0]['url'] if Record.objects.filter(
            mid=obj.mid, platform='bilibili') else ''
        return video_url


class LoginSerializer(serializers.ModelSerializer):
    code = serializers.CharField(max_length=128, write_only=True)
    access = serializers.CharField(label='请求密钥', max_length=255, read_only=True)

    class Meta:
        model = User
        fields = ['code', 'access']
        extra_kwargs = {
            'access': {'read_only': True}
        }

    def create(self, validated_data):
        try:
            res = self.context["request"].data
            code = res['code']
            if not code:
                logger.warning('Login without jscode.')
                raise MyValidationError(RetCode.STATUS_USER_GET_CODE_FAILED)
            r = get_openid(code)
            if not r.get('openid'):
                logger.warning('Failed to get openid.')
                raise MyValidationError(RetCode.STATUS_USER_GET_OPENID_FAILED)
            openid = r['openid']
            encrypt_openid_str = encrypt_openid(openid)
            nickname = res['userInfo']['nickName'] if 'nickName' in res['userInfo'] else ''
            avatar = res['userInfo']['avatarUrl'] if 'avatarUrl' in res['userInfo'] else ''
            user = User.objects.filter(openid=encrypt_openid_str).first()
            # 如果user不存在，数据库创建user
            if not user:
                nickname = get_uuid()
                user = User.objects.create(
                    nickname=nickname,
                    avatar=avatar,
                    openid=encrypt_openid_str)
            else:
                User.objects.filter(openid=encrypt_openid_str).update(
                    nickname=nickname,
                    avatar=avatar,
                    is_delete=0)
            return user
        except Exception as e:
            logger.error("e:{}, traceback:{}".format(e, traceback.format_exc()))
            raise MyValidationError(RetCode.STATUS_USER_LOGIN_FAILED)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        refresh = RefreshToken.for_user(instance)
        access = str(refresh.access_token)
        encrypt_access = make_signature(access)
        data['user_id'] = instance.id
        data['access'] = access
        data['level'] = instance.level
        data['gitee_name'] = instance.gitee_name
        data['nickname'] = instance.nickname
        data['activity_level'] = instance.activity_level
        data['agree_privacy_policy'] = instance.agree_privacy_policy
        User.objects.filter(id=instance.id).update(signature=encrypt_access)
        return data


class UsersInGroupSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'nickname', 'gitee_name', 'avatar']


class UserGroupSerializer(ModelSerializer):
    group_name = serializers.CharField(source='group.group_name', read_only=True)
    etherpad = serializers.CharField(source='group.etherpad', read_only=True)
    maillist = serializers.CharField(source='group.maillist', read_only=True)

    class Meta:
        model = GroupUser
        fields = ['group', 'group_name', 'etherpad', 'maillist']


class UserInfoSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['level', 'gitee_name', 'activity_level', 'nickname', 'avatar']


class GroupUserSerializer(ModelSerializer):
    nickname = serializers.CharField(source='user.nickname', max_length=40, read_only=True)
    gitee_name = serializers.CharField(source='user.gitee_name', max_length=40, read_only=True)
    avatar = serializers.CharField(source='user.avatar', max_length=256, read_only=True)

    class Meta:
        model = GroupUser
        fields = ['user', 'nickname', 'gitee_name', 'avatar']


class SigsSerializer(ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'group_name', 'home_page', 'maillist', 'irc', 'owners']


class MeetingsDataSerializer(ModelSerializer):
    avatar = serializers.CharField(source='user.avatar', max_length=255, read_only=True)

    class Meta:
        model = Meeting
        fields = ('id', 'date', 'start', 'end', 'duration', 'avatar')


class CollectSerializer(ModelSerializer):
    class Meta:
        model = Collect
        fields = ['meeting']


class AllMeetingsSerializer(ModelSerializer):
    class Meta:
        model = Meeting
        fields = '__all__'


class SponsorSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'nickname', 'avatar', 'gitee_name']


class SponsorInfoSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'gitee_name']


class ActivitySerializer(ModelSerializer):
    class Meta:
        model = Activity
        fields = ['id', 'title', 'activity_type', 'poster', 'synopsis']


class ActivitiesSerializer(ModelSerializer):
    collection_id = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ['id', 'collection_id', 'title', 'date', 'activity_type', 'synopsis', 'live_address',
                  'address', 'detail_address', 'longitude', 'latitude', 'schedules', 'poster', 'status', 'user',
                  'start', 'end', 'join_url', 'replay_url', 'register_url']

    def get_collection_id(self, obj):
        user = None
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        try:
            return ActivityCollect.objects.filter(user_id=user.id, activity_id=obj.id).values()[0]['id']
        except IndexError:
            return


class ActivityRetrieveSerializer(ActivitiesSerializer):
    class Meta:
        model = Activity
        fields = ['id', 'collection_id', 'title', 'date', 'activity_type', 'synopsis', 'live_address',
                  'address', 'detail_address', 'longitude', 'latitude', 'schedules', 'poster', 'status', 'user',
                  'wx_code', 'start', 'end', 'join_url', 'replay_url', 'register_url']


class ActivityUpdateSerializer(ModelSerializer):
    class Meta:
        model = Activity
        fields = ['schedules']


class ActivityDraftUpdateSerializer(ModelSerializer):
    class Meta:
        model = Activity
        fields = ['title', 'date', 'activity_type', 'poster', 'schedules']


class ActivityCollectSerializer(ModelSerializer):
    class Meta:
        model = ActivityCollect
        fields = ['activity']


class ApplicantInfoSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'gitee_name']
