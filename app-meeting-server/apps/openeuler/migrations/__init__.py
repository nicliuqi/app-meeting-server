# Generated by Django 2.2 on 2023-08-17 19:56

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nickname', models.CharField(blank=True, max_length=40, null=True, verbose_name='昵称')),
                ('gitee_name', models.CharField(blank=True, max_length=40, null=True, verbose_name='gitee名称')),
                ('avatar', models.CharField(blank=True, max_length=255, null=True, verbose_name='用户头像')),
                ('gender',
                 models.SmallIntegerField(choices=[(0, '未知'), (1, '男'), (2, '女')], default=0, verbose_name='性别')),
                ('openid', models.CharField(blank=True, max_length=32, null=True, unique=True, verbose_name='openid')),
                ('password', models.CharField(blank=True, max_length=128, null=True, verbose_name='密码')),
                ('unionid',
                 models.CharField(blank=True, max_length=128, null=True, unique=True, verbose_name='unionid')),
                ('status', models.SmallIntegerField(choices=[(0, '未登陆'), (1, '登陆')], default=0, verbose_name='状态')),
                ('level', models.SmallIntegerField(choices=[(1, '普通用户'), (2, '授权用户'), (3, '管理员')], default=1,
                                                   verbose_name='权限级别')),
                ('signature', models.CharField(blank=True, max_length=255, null=True, verbose_name='个性签名')),
                ('create_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
                ('last_login', models.DateTimeField(auto_now=True, null=True, verbose_name='上次登录时间')),
                ('name', models.CharField(blank=True, max_length=20, null=True, verbose_name='姓名')),
                ('telephone', models.CharField(blank=True, max_length=11, null=True, verbose_name='手机号码')),
                ('email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='个人邮箱')),
                ('company', models.CharField(blank=True, max_length=50, null=True, verbose_name='单位')),
                ('profession', models.CharField(blank=True, max_length=30, null=True, verbose_name='职业')),
                ('enterprise', models.CharField(blank=True, max_length=30, null=True, verbose_name='企业')),
                ('activity_level', models.SmallIntegerField(choices=[(1, '普通'), (2, '活动发起人'), (3, '管理员')], default=1,
                                                            verbose_name='活动权限')),
                ('register_number', models.IntegerField(default=0, verbose_name='报名次数')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=50, verbose_name='活动标题')),
                ('date', models.CharField(max_length=30, verbose_name='活动日期')),
                ('activity_type', models.SmallIntegerField(choices=[(1, '线下'), (2, '线上')], verbose_name='活动类型')),
                ('synopsis', models.TextField(blank=True, null=True, verbose_name='活动简介')),
                ('live_address', models.CharField(blank=True, max_length=255, null=True, verbose_name='直播地址')),
                ('address', models.CharField(blank=True, max_length=100, null=True, verbose_name='地理位置')),
                ('detail_address', models.CharField(blank=True, max_length=100, null=True, verbose_name='详细地址')),
                ('longitude',
                 models.DecimalField(blank=True, decimal_places=5, max_digits=8, null=True, verbose_name='经度')),
                ('latitude',
                 models.DecimalField(blank=True, decimal_places=5, max_digits=8, null=True, verbose_name='纬度')),
                ('schedules', models.TextField(blank=True, null=True, verbose_name='日程')),
                ('poster', models.SmallIntegerField(choices=[(1, '主题1'), (2, '主题2'), (3, '主题3'), (4, '主题4')], default=1,
                                                    verbose_name='海报')),
                ('status', models.SmallIntegerField(choices=[(1, '草稿'), (2, '审核中'), (3, '报名中'), (4, '进行中'), (5, '已结束')],
                                                    default=1, verbose_name='状态')),
                ('enterprise', models.CharField(blank=True, max_length=50, null=True, verbose_name='企业')),
                ('wx_code', models.TextField(blank=True, null=True, verbose_name='微信二维码')),
                ('is_delete',
                 models.SmallIntegerField(choices=[(0, '未删除'), (1, '已删除')], default=0, verbose_name='是否删除')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('start', models.CharField(blank=True, max_length=10, null=True, verbose_name='开始时间')),
                ('end', models.CharField(blank=True, max_length=10, null=True, verbose_name='结束时间')),
                ('start_url', models.TextField(blank=True, null=True, verbose_name='主持人入口')),
                ('join_url', models.CharField(blank=True, max_length=255, null=True, verbose_name='观众入口')),
                ('sign_url', models.CharField(blank=True, max_length=255, null=True, verbose_name='签到二维码')),
                ('mid', models.CharField(blank=True, max_length=20, null=True, verbose_name='网络研讨会id')),
                ('replay_url', models.CharField(blank=True, max_length=255, null=True, verbose_name='回放地址')),
                (
                'user', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group_name', models.CharField(max_length=128, unique=True, verbose_name='组名')),
                ('home_page', models.CharField(blank=True, max_length=128, null=True, verbose_name='首页')),
                ('maillist', models.EmailField(blank=True, max_length=254, null=True, verbose_name='邮件列表')),
                ('irc', models.CharField(blank=True, max_length=30, null=True, verbose_name='IRC频道')),
                ('etherpad', models.CharField(blank=True, max_length=255, null=True, verbose_name='etherpad')),
                ('owners', models.TextField(blank=True, null=True, verbose_name='maintainer列表')),
                ('app_home_page', models.CharField(blank=True, max_length=128, null=True, verbose_name='app首页')),
                ('description', models.CharField(blank=True, max_length=255, null=True, verbose_name='组描述')),
            ],
        ),
        migrations.CreateModel(
            name='Record',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mid', models.CharField(max_length=12, verbose_name='会议id')),
                ('platform', models.CharField(max_length=50, verbose_name='平台')),
                ('url', models.CharField(blank=True, max_length=128, null=True, verbose_name='播放地址')),
                ('thumbnail', models.CharField(blank=True, max_length=128, null=True, verbose_name='缩略图')),
            ],
        ),
        migrations.CreateModel(
            name='Video',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mid', models.CharField(max_length=12, verbose_name='会议id')),
                ('topic', models.CharField(max_length=50, verbose_name='会议名称')),
                ('community', models.CharField(blank=True, max_length=40, null=True, verbose_name='社区')),
                ('group_name', models.CharField(max_length=50, verbose_name='所属sig组')),
                ('agenda', models.TextField(blank=True, null=True, verbose_name='会议简介')),
                ('attenders', models.TextField(blank=True, null=True, verbose_name='参会人')),
                ('start', models.CharField(blank=True, max_length=30, null=True, verbose_name='记录开始时间')),
                ('end', models.CharField(blank=True, max_length=30, null=True, verbose_name='记录结束时间')),
                ('total_size', models.IntegerField(blank=True, null=True, verbose_name='总文件大小')),
                ('download_url', models.CharField(blank=True, max_length=255, null=True, verbose_name='下载地址')),
            ],
        ),
        migrations.CreateModel(
            name='Meeting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('topic', models.CharField(max_length=128, verbose_name='会议主题')),
                ('community', models.CharField(blank=True, max_length=40, null=True, verbose_name='社区')),
                ('group_name', models.CharField(default='', max_length=40, verbose_name='SIG组')),
                ('sponsor', models.CharField(max_length=20, verbose_name='发起人')),
                ('date', models.CharField(max_length=30, verbose_name='会议日期')),
                ('start', models.CharField(max_length=30, verbose_name='会议开始时间')),
                ('end', models.CharField(max_length=30, verbose_name='会议结束时间')),
                ('duration', models.IntegerField(blank=True, null=True, verbose_name='会议时长')),
                ('agenda', models.TextField(blank=True, default='', null=True, verbose_name='议程')),
                ('etherpad', models.CharField(blank=True, max_length=255, null=True, verbose_name='etherpad')),
                ('emaillist', models.TextField(blank=True, null=True, verbose_name='邮件列表')),
                ('host_id', models.EmailField(blank=True, max_length=254, null=True, verbose_name='host_id')),
                ('mid', models.CharField(max_length=20, verbose_name='会议id')),
                ('timezone', models.CharField(blank=True, max_length=50, null=True, verbose_name='时区')),
                ('password', models.CharField(blank=True, max_length=128, null=True, verbose_name='密码')),
                ('start_url', models.TextField(blank=True, null=True, verbose_name='开启会议url')),
                ('join_url', models.CharField(blank=True, max_length=128, null=True, verbose_name='进入会议url')),
                ('create_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
                ('is_delete', models.SmallIntegerField(choices=[(0, '否'), (1, '是')], default=0, verbose_name='是否删除')),
                ('mplatform',
                 models.CharField(blank=True, default='zoom', max_length=20, null=True, verbose_name='第三方会议平台')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='meetings.Group')),
                (
                'user', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feedback_type', models.SmallIntegerField(choices=[(1, '问题反馈'), (2, '产品建议')], verbose_name='反馈类型')),
                ('feedback_email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='反馈邮箱')),
                ('feedback_content', models.TextField(blank=True, null=True, verbose_name='反馈内容')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                (
                'user', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Collect',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meeting', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='meetings.Meeting')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ActivitySign',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='meetings.Activity')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ActivityRegister',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='meetings.Activity')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ActivityCollect',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='meetings.Activity')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='GroupUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='meetings.Group')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('group', 'user')},
            },
        ),
    ]
