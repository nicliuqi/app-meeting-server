import logging
import traceback

from django.conf import settings
from django.db import transaction
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from app_meeting_server.utils.common import get_uuid, encrypt_openid, refresh_token_and_refresh_token, get_cur_date
from app_meeting_server.utils.ret_code import RetCode
from app_meeting_server.utils.wx_apis import get_openid
from mindspore.models import Group, Meeting, Collect, User, GroupUser, City, CityUser, Activity, ActivityCollect
from app_meeting_server.utils.check_params import check_group_id, check_user_ids
from app_meeting_server.utils.ret_api import MyValidationError

logger = logging.getLogger('log')


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
                logger.warning('Login without code.')
                raise MyValidationError(RetCode.STATUS_USER_GET_CODE_FAILED)
            r = get_openid(code)
            if not r.get('openid'):
                logger.warning('Failed to get openid.')
                raise MyValidationError(RetCode.STATUS_USER_GET_OPENID_FAILED)
            openid = r['openid']
            encrypt_openid_str = encrypt_openid(openid)
            user = User.objects.filter(openid=encrypt_openid_str).exclude(nickname=settings.ANONYMOUS_NAME).first()
            # if user not exist, and need to create
            cur = get_cur_date()
            if not user:
                nickname = get_uuid()
                avatar = settings.WX_AVATAR_URL
                user = User.objects.create(
                    nickname=nickname,
                    avatar=avatar,
                    openid=encrypt_openid_str,
                    last_login=cur)
            else:
                User.objects.filter(openid=encrypt_openid_str).update(is_delete=0, last_login=cur)
            return user
        except Exception as e:
            logger.error("e:{}, traceback:{}".format(e, traceback.format_exc()))
            raise MyValidationError(RetCode.STATUS_USER_LOGIN_FAILED)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        access_token, refresh_token = refresh_token_and_refresh_token(instance)
        data['refresh'] = refresh_token
        data['access'] = access_token
        data['user_id'] = instance.id
        data['level'] = instance.level
        data['gitee_name'] = instance.gitee_name
        data['nickname'] = instance.nickname
        data['avatar'] = instance.avatar
        data['activity_level'] = instance.activity_level
        data['agree_privacy_policy'] = instance.agree_privacy_policy
        return data


class UsersSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'nickname', 'gitee_name', 'avatar']


class GroupsSerializer(ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']


class SigsSerializer(ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name", "group_type", "create_time"]


class CitiesSerializer(ModelSerializer):
    class Meta:
        model = City
        fields = ["id", "name", "etherpad"]


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
        users = User.objects.filter(id__in=validated_data['ids'], is_delete=0). \
            exclude(nickname=settings.ANONYMOUS_NAME)
        group_id = Group.objects.filter(id=validated_data['group_id']).first()
        try:
            result_list = list()
            with transaction.atomic():
                for user in users:
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


class CityUserAddSerializer(ModelSerializer):
    ids = serializers.CharField(max_length=255, write_only=True)
    city_id = serializers.CharField(max_length=255, write_only=True)

    class Meta:
        model = CityUser
        fields = ['city_id', 'ids']

    def validate_ids(self, value):
        return check_user_ids(value)

    def validate_city_id(self, value):
        return check_group_id(City, value)

    def create(self, validated_data):
        users = User.objects.filter(id__in=validated_data['ids']).filter(is_delete=True).exclude(
            nickname=settings.ANONYMOUS_NAME)
        city_id = City.objects.filter(id=validated_data['city_id']).first()
        try:
            with transaction.atomic():
                for user in users:
                    CityUser.objects.create(city_id=city_id.id, user_id=int(user.id))
                    User.objects.filter(id=int(user.id), level=1).update(level=2)
                    if not GroupUser.objects.filter(group_id=1, user_id=int(user.id)):
                        GroupUser.objects.create(group_id=1, user_id=int(user.id))
            return True
        except Exception as e:
            logger.error('Failed to add activity sponsors.and e:{}'.format(str(e)))
            raise MyValidationError(RetCode.INTERNAL_ERROR)


class CityUserDelSerializer(ModelSerializer):
    ids = serializers.CharField(max_length=255, write_only=True)
    city_id = serializers.CharField(max_length=255, write_only=True)

    class Meta:
        model = CityUser
        fields = ['city_id', 'ids']

    def validate_ids(self, value):
        return check_user_ids(value)

    def validate_city_id(self, value):
        return check_group_id(City, value)

    def create(self, validated_data):
        city_id = validated_data.get('city_id')
        ids_list = validated_data.get('ids_list')
        with transaction.atomic():
            CityUser.objects.filter(city_id=city_id, user_id__in=ids_list).delete()
            for user_id in ids_list:
                if not CityUser.objects.filter(user_id=user_id):
                    GroupUser.objects.filter(group_id=1, user_id=int(user_id)).delete()
        return True


class UpdateUserInfoSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'gitee_name']


class UserInfoSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'level', 'gitee_name', 'activity_level', 'nickname', 'avatar']


class UserGroupSerializer(ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)
    group_type = serializers.CharField(source='group.group_type', read_only=True)
    etherpad = serializers.CharField(source='group.etherpad', read_only=True)
    description = serializers.SerializerMethodField()

    class Meta:
        model = GroupUser
        fields = ['group', 'group_name', 'group_type', 'etherpad', 'description']

    def get_description(self, obj):
        if Group.objects.get(id=obj.group_id).group_type == 1:
            return 'SIG会议'
        elif Group.objects.get(id=obj.group_id).group_type == 2:
            return 'MSG会议'
        elif Group.objects.get(id=obj.group_id).group_type == 3:
            return '专家委员会'
        else:
            return ''


class UserCitySerializer(ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)
    etherpad = serializers.CharField(source='city.etherpad', read_only=True)

    class Meta:
        model = CityUser
        fields = ['city', 'city_name', 'etherpad']


class MeetingSerializer(ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['id', 'topic', 'sponsor', 'meeting_type', 'city', 'group_name', 'date', 'start', 'end', 'etherpad',
                  'agenda', 'emaillist', 'user_id', 'group_id']
        extra_kwargs = {
            'mid': {'read_only': True},
            'join_url': {'read_only': True},
            'group_name': {'required': True},
            'meeting_type': {'required': True}
        }


class MeetingDelSerializer(ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['mmid']


class MeetingsListSerializer(ModelSerializer):
    collection_id = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = ['id', 'collection_id', 'user_id', 'group_id', 'topic', 'sponsor', 'group_name', 'city', 'date',
                  'start', 'end', 'agenda', 'etherpad', 'mid', 'mmid', 'join_url', 'replay_url', 'mplatform']

    def get_collection_id(self, obj):
        user = None
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        try:
            return Collect.objects.filter(user_id=user.id, meeting_id=obj.id).values()[0]['id']
        except IndexError:
            return


class CollectSerializer(ModelSerializer):
    class Meta:
        model = Collect
        fields = ['meeting']


class SponsorSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'nickname', 'gitee_name', 'avatar']


class ActivitySerializer(ModelSerializer):
    class Meta:
        model = Activity
        fields = ['id', 'title', 'activity_type', 'poster', 'synopsis']


class ActivityUpdateSerializer(ModelSerializer):
    class Meta:
        model = Activity
        fields = ['schedules', 'replay_url']


class ActivityDraftUpdateSerializer(ModelSerializer):
    class Meta:
        model = Activity
        fields = '__all__'


class ActivitiesSerializer(ModelSerializer):
    collection_id = serializers.SerializerMethodField()
    register_id = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ['id', 'collection_id', 'title', 'start_date', 'end_date', 'activity_category',
                  'activity_type', 'register_method', 'register_url', 'synopsis', 'address', 'detail_address',
                  'online_url', 'longitude', 'latitude', 'schedules', 'poster', 'status', 'user', 'replay_url']

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
        fields = ['id', 'collection_id', 'register_id', 'title', 'start_date', 'end_date', 'activity_category',
                  'activity_type', 'register_method', 'register_url', 'synopsis', 'address', 'detail_address',
                  'online_url', 'longitude', 'latitude', 'schedules', 'poster', 'status', 'user', 'wx_code', 'sign_url', 'replay_url']


class ActivityCollectSerializer(ModelSerializer):
    class Meta:
        model = ActivityCollect
        fields = ['activity']


class ApplicantInfoSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'gitee_name']
