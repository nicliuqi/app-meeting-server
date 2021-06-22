import requests
import logging
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from meetings.models import Group, Meeting, Collect, User, GroupUser, Feedback

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
            r = requests.get(
                url='https://api.weixin.qq.com/sns/jscode2session?',
                params={
                    'appid': settings.MINDSPORE_APP_CONF['appid'],
                    'secret': settings.MINDSPORE_APP_CONF['secret'],
                    'js_code': code,
                    'grant_type': 'authorization_code'
                }
            ).json()
            if 'openid' not in r:
                logger.warning('Failed to get openid.')
                raise serializers.ValidationError('未获取到openid', code='code_error')
            openid = r['openid']
            nickname = res['userInfo']['nickName'] if 'nickName' in res['userInfo'] else ''
            avatar = res['userInfo']['avatarUrl'] if 'avatarUrl' in res['userInfo'] else ''
            gender = res['userInfo']['gender'] if 'gender' in res['userInfo'] else 0
            user = User.objects.filter(openid=openid).first()
            # 如果user不存在，数据库创建user
            if not user:
                user = User.objects.create(
                    nickname=nickname,
                    avatar=avatar,
                    gender=gender,
                    gitee_name=nickname,
                    status=1,
                    password=make_password(openid),
                    openid=openid)
            else:
                User.objects.filter(openid=openid).update(
                    nickname=nickname,
                    avatar=avatar,
                    gender=gender)
            return user
        except Exception as e:
            logger.error('Invalid params')
            logger.error(e)
            raise serializers.ValidationError('非法参数', code='code_error')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        refresh = RefreshToken.for_user(instance)
        data['user_id'] = instance.id
        data['access'] = str(refresh.access_token)
        data['level'] = instance.level
        data['gitee_name'] = instance.gitee_name
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
        users = User.objects.filter(id__in=validated_data['ids'])
        group_id = Group.objects.filter(id=validated_data['group_id']).first()
        try:
            for id in users:
                groupuser = GroupUser.objects.create(group_id=group_id.id, user_id=int(id.id))
                User.objects.filter(id=int(id.id), level=1).update(level=2)
            return groupuser
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


class UserInfoSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'level', 'gitee_name', 'email', 'telephone']


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


class MeetingSerializer(ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['id', 'topic', 'sponsor', 'meeting_type', 'group_name', 'date', 'start', 'end', 'etherpad', 'agenda', 'emaillist', 'user_id', 'group_id']
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
        fields = ['id', 'collection_id', 'user_id', 'group_id', 'topic', 'sponsor', 'group_name', 'date', 'start',
                  'end', 'agenda', 'etherpad', 'mid', 'mmid', 'join_url', 'replay_url']

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


class FeedbackSerializer(ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['feedback_type', 'feedback_email', 'feedback_content']
