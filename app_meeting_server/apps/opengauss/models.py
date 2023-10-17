from django.db import models
from app_meeting_server.utils.models import MyAbstractBaseUser, BaseMeeting


class User(MyAbstractBaseUser):
    """用户表"""
    gid = models.IntegerField(verbose_name='Gitee用户唯一标识')
    gitee_id = models.CharField(verbose_name='GiteeID', max_length=50)
    name = models.CharField(verbose_name='昵称', max_length=50)
    avatar = models.CharField(verbose_name='头像', max_length=255)
    email = models.EmailField(verbose_name='邮箱')
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True, blank=True)
    expire_time = models.IntegerField(verbose_name='过期时间', default=0)

    USERNAME_FIELD = 'gitee_id'

    class Meta:
        db_table = "meetings_user"
        verbose_name = "meetings_user"
        verbose_name_plural = verbose_name


class Group(models.Model):
    name = models.CharField(verbose_name='sig组名称', max_length=50)
    members = models.TextField(verbose_name='sig组成员')
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = "meetings_group"
        verbose_name = "meetings_group"
        verbose_name_plural = verbose_name


class Meeting(BaseMeeting):
    """会议表"""
    avatar = models.CharField(verbose_name='发起人头像', max_length=255, null=True, blank=True)
    timezone = models.CharField(verbose_name='时区', max_length=50, null=True, blank=True)
    start_url = models.TextField(verbose_name='开启会议url', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    group = models.ForeignKey(Group, on_delete=models.DO_NOTHING)
    mplatform = models.CharField(verbose_name='第三方会议平台', max_length=20, null=True, blank=True, default='zoom')
    sequence = models.IntegerField(verbose_name='序列号', default=0)

    class Meta:
        db_table = "meetings_meeting"
        verbose_name = "meetings_meeting"
        verbose_name_plural = verbose_name


class Video(models.Model):
    """会议记录表"""
    mid = models.CharField(verbose_name='会议id', max_length=12)
    topic = models.CharField(verbose_name='会议名称', max_length=50)
    community = models.CharField(verbose_name='社区', max_length=40, null=True, blank=True)
    group_name = models.CharField(verbose_name='所属sig组', max_length=50)
    agenda = models.TextField(verbose_name='会议简介', null=True, blank=True)
    attenders = models.TextField(verbose_name='参会人', null=True, blank=True)
    start = models.CharField(verbose_name='记录开始时间', max_length=30, null=True, blank=True)
    end = models.CharField(verbose_name='记录结束时间', max_length=30, null=True, blank=True)
    total_size = models.IntegerField(verbose_name='总文件大小', null=True, blank=True)
    download_url = models.CharField(verbose_name='下载地址', max_length=255, null=True, blank=True)
    replay_url = models.CharField(verbose_name='回放地址', max_length=255, null=True, blank=True)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = "meetings_video"
        verbose_name = "meetings_video"
        verbose_name_plural = verbose_name


class Record(models.Model):
    """录像表"""
    mid = models.CharField(verbose_name='会议id', max_length=12)
    platform = models.CharField(verbose_name='平台', max_length=50)
    url = models.CharField(verbose_name='播放地址', max_length=255, null=True, blank=True)
    thumbnail = models.CharField(verbose_name='缩略图', max_length=255, null=True, blank=True)

    class Meta:
        db_table = "meetings_record"
        verbose_name = "meetings_record"
        verbose_name_plural = verbose_name
