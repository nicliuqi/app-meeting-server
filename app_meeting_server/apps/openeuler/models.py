from app_meeting_server.utils.models import BaseUser, BaseMeeting, BaseActivity
from django.db import models


class User(BaseUser):
    """用户表"""

    USERNAME_FIELD = 'id'

    class Meta:
        db_table = "meetings_user"
        verbose_name = "meetings_user"
        verbose_name_plural = verbose_name


class Group(models.Model):
    """SIG组表"""
    group_name = models.CharField(verbose_name='组名', max_length=128, unique=True)
    home_page = models.CharField(verbose_name='首页', max_length=128, null=True, blank=True)
    maillist = models.EmailField(verbose_name='邮件列表', null=True, blank=True)
    irc = models.CharField(verbose_name='IRC频道', max_length=30, null=True, blank=True)
    etherpad = models.CharField(verbose_name='etherpad', max_length=255, null=True, blank=True)
    owners = models.TextField(verbose_name='maintainer列表', null=True, blank=True)
    app_home_page = models.CharField(verbose_name='app首页', max_length=128, null=True, blank=True)
    description = models.CharField(verbose_name='组描述', max_length=255, null=True, blank=True)

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


class Meeting(BaseMeeting):
    """会议表"""
    start_url = models.TextField(verbose_name='开启会议url', null=True, blank=True)
    timezone = models.CharField(verbose_name='时区', max_length=50, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    group = models.ForeignKey(Group, on_delete=models.DO_NOTHING)
    mplatform = models.CharField(verbose_name='第三方会议平台', max_length=20, null=True, blank=True, default='zoom')

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


class Video(models.Model):
    """会议记录表"""
    mid = models.CharField(verbose_name='会议id', max_length=12)
    topic = models.CharField(verbose_name='会议名称', max_length=50)
    community = models.CharField(verbose_name='社区', max_length=40, null=True, blank=True)
    group_name = models.CharField(verbose_name='所属sig组', max_length=50)
    agenda = models.TextField(verbose_name='会议简介', blank=True, null=True)
    attenders = models.TextField(verbose_name='参会人', blank=True, null=True)
    start = models.CharField(verbose_name='记录开始时间', max_length=30, blank=True, null=True)
    end = models.CharField(verbose_name='记录结束时间', max_length=30, blank=True, null=True)
    total_size = models.IntegerField(verbose_name='总文件大小', blank=True, null=True)
    download_url = models.CharField(verbose_name='下载地址', max_length=255, blank=True, null=True)

    class Meta:
        db_table = "meetings_video"
        verbose_name = "meetings_video"
        verbose_name_plural = verbose_name


class Record(models.Model):
    """录像表"""
    mid = models.CharField(verbose_name='会议id', max_length=12)
    platform = models.CharField(verbose_name='平台', max_length=50)
    url = models.CharField(verbose_name='播放地址', max_length=128, null=True, blank=True)
    thumbnail = models.CharField(verbose_name='缩略图', max_length=128, null=True, blank=True)

    class Meta:
        db_table = "meetings_record"
        verbose_name = "meetings_record"
        verbose_name_plural = verbose_name


class Activity(BaseActivity):
    """活动表"""
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    date = models.CharField(verbose_name='活动日期', max_length=30)
    live_address = models.CharField(verbose_name='直播地址', max_length=255, null=True, blank=True)
    start = models.CharField(verbose_name='开始时间', max_length=10, null=True, blank=True)
    end = models.CharField(verbose_name='结束时间', max_length=10, null=True, blank=True)
    start_url = models.TextField(verbose_name='主持人入口', null=True, blank=True)
    join_url = models.CharField(verbose_name='观众入口', max_length=255, null=True, blank=True)
    mid = models.CharField(verbose_name='网络研讨会id', max_length=20, null=True, blank=True)

    class Meta:
        db_table = "meetings_activity"
        verbose_name = "meetings_activity"
        verbose_name_plural = verbose_name


class ActivityCollect(models.Model):
    """用户收藏活动表"""
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('activity', 'user')
        db_table = "meetings_activitycollect"
        verbose_name = "meetings_activitycollect"
        verbose_name_plural = verbose_name
