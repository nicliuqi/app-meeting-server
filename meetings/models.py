from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models


class User(AbstractBaseUser):
    """用户表"""
    nickname = models.CharField(verbose_name='昵称', max_length=40, null=True, blank=True)
    gitee_name = models.CharField(verbose_name='gitee名称', max_length=40, null=True, blank=True)
    avatar = models.CharField(verbose_name='用户头像', max_length=255, null=True, blank=True)
    gender = models.SmallIntegerField(verbose_name='性别', choices=((0, '未知'), (1, '男'), (2, '女')),
                                      default=0)
    openid = models.CharField(verbose_name='openid', max_length=32, unique=True, null=True, blank=True)
    password = models.CharField('密码', max_length=128, null=True, blank=True)
    unionid = models.CharField(verbose_name='unionid', max_length=128, unique=True, null=True, blank=True)
    status = models.SmallIntegerField(verbose_name='状态', choices=((0, '未登陆'), (1, '登陆')), default=0)
    level = models.SmallIntegerField(verbose_name='权限级别', choices=((1, '普通用户'), (2, '授权用户'), (3, '管理员')),
                                     default=1)
    activity_level = models.SmallIntegerField(verbose_name='活动权限', choices=((1, '普通用户'), (2, '授权用户'), (3, '管理员')),
                                              default=1)
    signature = models.CharField(verbose_name='个性签名', max_length=255, blank=True, null=True)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True, blank=True)
    last_login = models.DateTimeField(verbose_name='上次登录时间', auto_now=True, null=True, blank=True)
    name = models.CharField(verbose_name='姓名', max_length=20, null=True, blank=True)
    wx_account = models.CharField(verbose_name='微信账号', max_length=100, null=True, blank=True)
    age = models.CharField(verbose_name='年龄', max_length=10, null=True, blank=True)
    telephone = models.CharField(verbose_name='手机号码', max_length=11, null=True, blank=True)
    email = models.EmailField(verbose_name='个人邮箱', null=True, blank=True)
    company = models.CharField(verbose_name='单位', max_length=50, null=True, blank=True)
    career_direction = models.CharField(verbose_name='职业方向', max_length=100, null=True, blank=True)
    profession = models.CharField(verbose_name='职业', max_length=100, null=True, blank=True)
    working_years = models.CharField(verbose_name='工作年限', max_length=10, null=True, blank=True)
    enterprise = models.CharField(verbose_name='企业', max_length=30, null=True, blank=True)
    register_number = models.IntegerField(verbose_name='报名次数', default=0)

    USERNAME_FIELD = 'openid'


class Group(models.Model):
    """用户组表"""
    name = models.CharField(verbose_name='组名', max_length=50)
    group_type = models.SmallIntegerField(verbose_name='组别', choices=((1, 'SIG'), (2, 'MSG'), (3, 'Pro')), null=True,
                                          blank=True)
    etherpad = models.CharField(verbose_name='etherpad', max_length=128, null=True, blank=True)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True, blank=True)


class GroupUser(models.Model):
    """组与用户表"""
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('group', 'user')


class City(models.Model):
    """城市表"""
    name = models.CharField(verbose_name='城市', max_length=20, unique=True)
    etherpad = models.CharField(verbose_name='etherpad', max_length=128, null=True, blank=True)


class CityUser(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('city', 'user')


class Meeting(models.Model):
    """会议表"""
    topic = models.CharField(verbose_name='会议主题', max_length=128)
    community = models.CharField(verbose_name='社区', max_length=40, null=True, blank=True)
    group_name = models.CharField(verbose_name='组名', max_length=40, default='')
    group_type = models.SmallIntegerField(verbose_name='组别', choices=((1, 'SIG'), (2, 'MSG'), (3, 'Pro')))
    city = models.CharField(verbose_name='城市', max_length=10, null=True, blank=True)
    sponsor = models.CharField(verbose_name='发起人', max_length=20)
    date = models.CharField(verbose_name='会议日期', max_length=30)
    start = models.CharField(verbose_name='会议开始时间', max_length=30)
    end = models.CharField(verbose_name='会议结束时间', max_length=30)
    duration = models.IntegerField(verbose_name='会议时长', null=True, blank=True)
    agenda = models.TextField(verbose_name='议程', default='', null=True, blank=True)
    etherpad = models.CharField(verbose_name='etherpad', max_length=255, null=True, blank=True)
    emaillist = models.TextField(verbose_name='邮件列表', null=True, blank=True)
    host_id = models.EmailField(verbose_name='host_id', null=True, blank=True)
    mid = models.CharField(verbose_name='会议id', max_length=20)
    password = models.CharField(verbose_name='密码', max_length=128, null=True, blank=True)
    join_url = models.CharField(verbose_name='进入会议url', max_length=128, null=True, blank=True)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True, blank=True)
    is_delete = models.SmallIntegerField(verbose_name='是否删除', choices=((0, '否'), (1, '是')), default=0)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    group = models.ForeignKey(Group, on_delete=models.DO_NOTHING)
    meeting_type = models.SmallIntegerField(verbose_name='会议类型', choices=((1, 'SIG'), (2, 'MSG'), (3, '专家委员会')),
                                            null=True, blank=True)
    mmid = models.CharField(verbose_name='腾讯会议id', max_length=20, null=True, blank=True)
    replay_url = models.CharField(verbose_name='回放地址', max_length=255, null=True, blank=True)
    mplatform = models.CharField(verbose_name='第三方会议平台', max_length=20, null=True, blank=True, default='tencent')


class Collect(models.Model):
    """用户收藏会议表"""
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('meeting', 'user')


class Feedback(models.Model):
    """意见反馈表"""
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    feedback_type = models.SmallIntegerField(verbose_name='反馈类型', choices=((1, '问题反馈'), (2, '产品建议')))
    feedback_email = models.EmailField(verbose_name='反馈邮箱', null=True, blank=True)
    feedback_content = models.TextField(verbose_name='反馈内容', null=True, blank=True)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)


class Record(models.Model):
    """录像上传记录表"""
    meeting_code = models.CharField(verbose_name='会议号', max_length=20)
    file_size = models.CharField(verbose_name='视频大小', max_length=20)
    download_url = models.CharField(verbose_name='下载地址', max_length=255)


class Activity(models.Model):
    """活动表"""
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    title = models.CharField(verbose_name='活动标题', max_length=50)
    start_date = models.CharField(verbose_name='活动开始日期', max_length=30)
    end_date = models.CharField(verbose_name='活动结束日期', max_length=30)
    activity_category = models.SmallIntegerField(verbose_name='活动类别',
                                                 choices=((1, '课程'), (2, 'MSG'), (3, '赛事'), (4, '其他')))
    activity_type = models.SmallIntegerField(verbose_name='活动类型', choices=((1, '线下'), (2, '线上'), (3, '线上与线下')))
    address = models.CharField(verbose_name='地理位置', max_length=100, null=True, blank=True)
    detail_address = models.CharField(verbose_name='详细地址', max_length=100, null=True, blank=True)
    longitude = models.DecimalField(verbose_name='经度', max_digits=8, decimal_places=5, null=True, blank=True)
    latitude = models.DecimalField(verbose_name='纬度', max_digits=8, decimal_places=5, null=True, blank=True)
    register_method = models.SmallIntegerField(verbose_name='报名方式', choices=((1, '小程序报名'), (2, '跳转链接')))
    online_url = models.CharField(verbose_name='线上链接', max_length=255, null=True, blank=True)
    register_url = models.CharField(verbose_name='报名链接', max_length=255, null=True, blank=True)
    synopsis = models.TextField(verbose_name='活动简介', null=True, blank=True)
    schedules = models.TextField(verbose_name='日程', null=True, blank=True)
    poster = models.SmallIntegerField(verbose_name='海报', choices=((1, '主题1'), (2, '主题2'), (3, '主题3'), (4, '主题4')),
                                      default=1)
    status = models.SmallIntegerField(verbose_name='状态',
                                      choices=((1, '草稿'), (2, '审核中'), (3, '报名中'), (4, '进行中'), (5, '已结束')), default=1)
    wx_code = models.TextField(verbose_name='微信二维码', null=True, blank=True)
    is_delete = models.SmallIntegerField(verbose_name='是否删除', choices=((0, '未删除'), (1, '已删除')), default=0)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    sign_url = models.CharField(verbose_name='签到二维码', max_length=255, null=True, blank=True)
    replay_url = models.CharField(verbose_name='回放地址', max_length=255, null=True, blank=True)


class ActivityCollect(models.Model):
    """活动收藏表"""
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('activity', 'user')


class ActivityRegister(models.Model):
    """活动报名表"""
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('activity', 'user')


class ActivitySign(models.Model):
    """活动签到表"""
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('activity', 'user')
