import logging
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from app_meeting_server.utils import wx_apis, crypto_gcm
from app_meeting_server.utils.common import get_uuid
from mindspore.models import Group, Meeting, Collect, User, GroupUser, City, CityUser, Activity, ActivityCollect
from django.conf import settings

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
                logger.warning('Login without jscode.')
                raise serializers.ValidationError('需要code', code='code_error')
            r = wx_apis.get_openid(code)
            if not r.get('openid'):
                logger.warning('Failed to get openid.')
                raise serializers.ValidationError('未获取到openid', code='code_error')
            openid = r['openid']
            encrypt_openid = crypto_gcm.aes_gcm_encrypt(openid, settings.AES_GCM_SECRET, settings.AES_GCM_IV)
            nickname = res['userInfo']['nickName'] if 'nickName' in res['userInfo'] else ''
            avatar = res['userInfo']['avatarUrl'] if 'avatarUrl' in res['userInfo'] else ''
            user = User.objects.filter(openid=encrypt_openid).first()
            if nickname == '微信用户':
                nickname = get_uuid()
            # 如果user不存在，数据库创建user
            if not user:
                user = User.objects.create(
                    nickname=nickname,
                    avatar=avatar,
                    openid=encrypt_openid)
            else:
                User.objects.filter(openid=encrypt_openid).update(
                    nickname=nickname,
                    avatar=avatar,
                    is_delete=0)
            return user
        except Exception as e:
            logger.error('Invalid params')
            logger.error(e)
            raise serializers.ValidationError('非法参数', code='code_error')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        refresh = RefreshToken.for_user(instance)
        data['user_id'] = instance.id
        access = str(refresh.access_token)
        encrypt_access = crypto_gcm.aes_gcm_encrypt(access, settings.AES_GCM_SECRET, settings.AES_GCM_IV)
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


class SigsSerializer(ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'


class GroupsSerializer(ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'


class CitiesSerializer(ModelSerializer):
    class Meta:
        model = City
        fields = '__all__'


class GroupUserAddSerializer(ModelSerializer):
    ids = serializers.CharField(max_length=255, write_only=True)
    group_id = serializers.CharField(max_length=255, write_only=True)

    class Meta:
        model = GroupUser
        fields = ['group_id', 'ids']

    def validate_ids(self, value):
        try:
            list_ids = value.split('-')
        except Exception as e:
            logger.error('Invalid input.The ids should be like "1-2-3".')
            logger.error(e)
            raise serializers.ValidationError('输入格式有误！', code='code_error')
        return list_ids

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
            logger.error('Failed to add maintainers to the group.')
            logger.error(e)
            raise serializers.ValidationError('创建失败！', code='code_error')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['code'] = 201
        data['msg'] = u'添加成功'
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
        try:
            list_ids = value.split('-')
        except Exception as e:
            logger.error('Invalid input.The ids should be like "1-2-3".')
            logger.error(e)
            raise serializers.ValidationError('输入格式有误！', code='code_error')
        return list_ids

    def create(self, validated_data):
        users = User.objects.filter(id__in=validated_data['ids'])
        city_id = City.objects.filter(id=validated_data['city_id']).first()
        try:
            for id in users:
                cityuser = CityUser.objects.create(city_id=city_id.id, user_id=int(id.id))
                User.objects.filter(id=int(id.id), level=1).update(level=2)
                if not GroupUser.objects.filter(group_id=1, user_id=int(id.id)):
                    GroupUser.objects.create(group_id=1, user_id=int(id.id))
            return cityuser
        except Exception as e:
            logger.error('Failed to add activity sponsors.')
            logger.error(e)
            raise serializers.ValidationError('创建失败！', code='code_error')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['code'] = 201
        data['msg'] = u'添加成功'
        return data


class CityUserDelSerializer(ModelSerializer):
    ids = serializers.CharField(max_length=255, write_only=True)
    city_id = serializers.CharField(max_length=255, write_only=True)

    class Meta:
        model = CityUser
        fields = ['city_id', 'ids']


class UserInfoSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'level', 'activity_level', 'gitee_name']


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
        if Group.objects.get(id=obj.group_id).group_type == 2:
            return 'MSG会议'
        if Group.objects.get(id=obj.group_id).group_type == 3:
            return '专家委员会'


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
            'group_name': {'required': True },
            'meeting_type': {'required': True}
        }


class MeetingDelSerializer(ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['mmid']


class MeetingDetailSerializer(ModelSerializer):
    class Meta:
        model = Meeting
        fields = '__all__'


class MeetingsListSerializer(ModelSerializer):
    collection_id = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = ['id', 'collection_id', 'user_id', 'group_id', 'topic', 'sponsor', 'group_name', 'city', 'date', 'start',
                  'end', 'agenda', 'etherpad', 'mid', 'mmid', 'join_url', 'replay_url', 'mplatform']

    def get_collection_id(self, obj):
        user = None
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        try:
            return Collect.objects.filter(user_id=user.pk, meeting_id=obj.id).values()[0]['id']
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
        fields = ['schedules', 'replay_url', 'online_url']


class ActivityDraftUpdateSerializer(ModelSerializer):
    class Meta:
        model = Activity
        fields = '__all__'


class ActivitiesSerializer(ModelSerializer):
    collection_id = serializers.SerializerMethodField()
    register_id = serializers.SerializerMethodField()
    register_count = serializers.SerializerMethodField()

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
            return ActivityCollect.objects.filter(user_id=user.pk, activity_id=obj.id).values()[0]['id']
        except IndexError:
            return


class ActivityRetrieveSerializer(ActivitiesSerializer):
    class Meta:
        model = Activity
        fields = ['id', 'collection_id', 'register_id', 'title', 'start_date', 'end_date', 'activity_category',
                  'activity_type', 'register_method', 'register_url', 'synopsis', 'address', 'detail_address',
                  'online_url', 'longitude', 'latitude', 'schedules', 'poster', 'status', 'user', 'register_count',
                  'wx_code', 'sign_url', 'replay_url']


class ActivityCollectSerializer(ModelSerializer):
    class Meta:
        model = ActivityCollect
        fields = ['activity']


class ApplicantInfoSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'gitee_name']
