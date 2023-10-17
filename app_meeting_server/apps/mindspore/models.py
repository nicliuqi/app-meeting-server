from app_meeting_server.utils.models import BaseUser, BaseMeeting
from django.db import models


class User(BaseUser):
    """用户表"""

    USERNAME_FIELD = 'openid'

    class Meta:
        db_table = "meetings_user"
        verbose_name = "meetings_user"
        verbose_name_plural = verbose_name


class Group(models.Model):
    """用户组表"""
    name = models.CharField(verbose_name='组名', max_length=50)
    group_type = models.SmallIntegerField(verbose_name='组别', choices=((1, 'SIG'), (2, 'MSG'), (3, 'Pro')), null=True,
                                          blank=True)
    etherpad = models.CharField(verbose_name='etherpad', max_length=128, null=True, blank=True)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = "meetings_group"
        verbose_name = "meetings_group"
        verbose_name_plural = verbose_name


class GroupUser(models.Model):
    """组与用户表"""
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('group', 'user')
        db_table = "meetings_groupuser"
        verbose_name = "meetings_groupuser"
        verbose_name_plural = verbose_name


class City(models.Model):
    """城市表"""
    name = models.CharField(verbose_name='城市', max_length=20, unique=True)
    etherpad = models.CharField(verbose_name='etherpad', max_length=128, null=True, blank=True)

    class Meta:
        db_table = "meetings_city"
        verbose_name = "meetings_city"
        verbose_name_plural = verbose_name


class CityUser(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('city', 'user')
        db_table = "meetings_cityuser"
        verbose_name = "meetings_cityuser"
        verbose_name_plural = verbose_name


class Meeting(BaseMeeting):
    """会议表"""
    group_type = models.SmallIntegerField(verbose_name='组别', choices=((1, 'SIG'), (2, 'MSG'), (3, 'Pro')))
    city = models.CharField(verbose_name='城市', max_length=10, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    group = models.ForeignKey(Group, on_delete=models.DO_NOTHING)
    meeting_type = models.SmallIntegerField(verbose_name='会议类型', choices=((1, 'SIG'), (2, 'MSG'), (3, '专家委员会')),
                                            null=True, blank=True)
    replay_url = models.CharField(verbose_name='回放地址', max_length=255, null=True, blank=True)
    mplatform = models.CharField(verbose_name='第三方会议平台', max_length=20, null=True, blank=True, default='tencent')

    class Meta:
        db_table = "meetings_meeting"
        verbose_name = "meetings_meeting"
        verbose_name_plural = verbose_name


class Collect(models.Model):
    """用户收藏会议表"""
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('meeting', 'user')
        db_table = "meetings_collect"
        verbose_name = "meetings_collect"
        verbose_name_plural = verbose_name


class Record(models.Model):
    """录像上传记录表"""
    meeting_code = models.CharField(verbose_name='会议号', max_length=20)
    file_size = models.CharField(verbose_name='视频大小', max_length=20)
    download_url = models.CharField(verbose_name='下载地址', max_length=255)

    class Meta:
        db_table = "meetings_record"
        verbose_name = "meetings_record"
        verbose_name_plural = verbose_name


class Activity(models.Model):
    """活动表"""
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    start_date = models.CharField(verbose_name='活动开始日期', max_length=30)
    end_date = models.CharField(verbose_name='活动结束日期', max_length=30)
    activity_category = models.SmallIntegerField(verbose_name='活动类别',
                                                 choices=((1, '课程'), (2, 'MSG'), (3, '赛事'), (4, '其他')))
    register_method = models.SmallIntegerField(verbose_name='报名方式', choices=((1, '小程序报名'), (2, '跳转链接')))
    online_url = models.CharField(verbose_name='线上链接', max_length=255, null=True, blank=True)

    class Meta:
        db_table = "meetings_activity"
        verbose_name = "meetings_activity"
        verbose_name_plural = verbose_name


class ActivityCollect(models.Model):
    """活动收藏表"""
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('activity', 'user')
        db_table = "meetings_activitycollect"
        verbose_name = "meetings_activitycollect"
        verbose_name_plural = verbose_name
