# Generated by Django 3.2.21 on 2023-10-09 15:19

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
                ('gender', models.SmallIntegerField(choices=[(0, '未知'), (1, '男'), (2, '女')], default=0, verbose_name='性别')),
                ('openid', models.CharField(blank=True, max_length=32, null=True, unique=True, verbose_name='openid')),
                ('password', models.CharField(blank=True, max_length=128, null=True, verbose_name='密码')),
                ('unionid', models.CharField(blank=True, max_length=128, null=True, unique=True, verbose_name='unionid')),
                ('status', models.SmallIntegerField(choices=[(0, '未登陆'), (1, '登陆')], default=0, verbose_name='状态')),
                ('level', models.SmallIntegerField(choices=[(1, '普通用户'), (2, '授权用户'), (3, '管理员')], default=1, verbose_name='权限级别')),
                ('activity_level', models.SmallIntegerField(choices=[(1, '普通用户'), (2, '授权用户'), (3, '管理员')], default=1, verbose_name='活动权限')),
                ('signature', models.CharField(blank=True, max_length=255, null=True, verbose_name='个性签名')),
                ('create_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
                ('last_login', models.DateTimeField(auto_now=True, null=True, verbose_name='上次登录时间')),
                ('name', models.CharField(blank=True, max_length=20, null=True, verbose_name='姓名')),
                ('wx_account', models.CharField(blank=True, max_length=100, null=True, verbose_name='微信账号')),
                ('age', models.CharField(blank=True, max_length=10, null=True, verbose_name='年龄')),
                ('telephone', models.CharField(blank=True, max_length=11, null=True, verbose_name='手机号码')),
                ('email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='个人邮箱')),
                ('company', models.CharField(blank=True, max_length=50, null=True, verbose_name='单位')),
                ('career_direction', models.CharField(blank=True, max_length=100, null=True, verbose_name='职业方向')),
                ('profession', models.CharField(blank=True, max_length=100, null=True, verbose_name='职业')),
                ('working_years', models.CharField(blank=True, max_length=10, null=True, verbose_name='工作年限')),
                ('enterprise', models.CharField(blank=True, max_length=30, null=True, verbose_name='企业')),
                ('register_number', models.IntegerField(default=0, verbose_name='报名次数')),
                ('agree_privacy_policy', models.BooleanField(default=False, verbose_name='同意隐私政策')),
                ('agree_privacy_policy_time', models.DateTimeField(blank=True, null=True, verbose_name='同意隐私政策时间')),
                ('agree_privacy_policy_version', models.CharField(blank=True, max_length=20, null=True, verbose_name='同意隐私政策版本')),
            ],
            options={
                'verbose_name': 'meetings_user',
                'verbose_name_plural': 'meetings_user',
                'db_table': 'meetings_user',
            },
        ),
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=50, verbose_name='活动标题')),
                ('start_date', models.CharField(max_length=30, verbose_name='活动开始日期')),
                ('end_date', models.CharField(max_length=30, verbose_name='活动结束日期')),
                ('activity_category', models.SmallIntegerField(choices=[(1, '课程'), (2, 'MSG'), (3, '赛事'), (4, '其他')], verbose_name='活动类别')),
                ('activity_type', models.SmallIntegerField(choices=[(1, '线下'), (2, '线上'), (3, '线上与线下')], verbose_name='活动类型')),
                ('address', models.CharField(blank=True, max_length=100, null=True, verbose_name='地理位置')),
                ('detail_address', models.CharField(blank=True, max_length=100, null=True, verbose_name='详细地址')),
                ('longitude', models.DecimalField(blank=True, decimal_places=5, max_digits=8, null=True, verbose_name='经度')),
                ('latitude', models.DecimalField(blank=True, decimal_places=5, max_digits=8, null=True, verbose_name='纬度')),
                ('register_method', models.SmallIntegerField(choices=[(1, '小程序报名'), (2, '跳转链接')], verbose_name='报名方式')),
                ('online_url', models.CharField(blank=True, max_length=255, null=True, verbose_name='线上链接')),
                ('register_url', models.CharField(blank=True, max_length=255, null=True, verbose_name='报名链接')),
                ('synopsis', models.TextField(blank=True, null=True, verbose_name='活动简介')),
                ('schedules', models.TextField(blank=True, null=True, verbose_name='日程')),
                ('poster', models.SmallIntegerField(choices=[(1, '主题1'), (2, '主题2'), (3, '主题3'), (4, '主题4')], default=1, verbose_name='海报')),
                ('status', models.SmallIntegerField(choices=[(1, '草稿'), (2, '审核中'), (3, '报名中'), (4, '进行中'), (5, '已结束')], default=1, verbose_name='状态')),
                ('wx_code', models.TextField(blank=True, null=True, verbose_name='微信二维码')),
                ('is_delete', models.SmallIntegerField(choices=[(0, '未删除'), (1, '已删除')], default=0, verbose_name='是否删除')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('sign_url', models.CharField(blank=True, max_length=255, null=True, verbose_name='签到二维码')),
                ('replay_url', models.CharField(blank=True, max_length=255, null=True, verbose_name='回放地址')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'meetings_activity',
                'verbose_name_plural': 'meetings_activity',
                'db_table': 'meetings_activity',
            },
        ),
        migrations.CreateModel(
            name='City',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20, unique=True, verbose_name='城市')),
                ('etherpad', models.CharField(blank=True, max_length=128, null=True, verbose_name='etherpad')),
            ],
            options={
                'verbose_name': 'meetings_city',
                'verbose_name_plural': 'meetings_city',
                'db_table': 'meetings_city',
            },
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='组名')),
                ('group_type', models.SmallIntegerField(blank=True, choices=[(1, 'SIG'), (2, 'MSG'), (3, 'Pro')], null=True, verbose_name='组别')),
                ('etherpad', models.CharField(blank=True, max_length=128, null=True, verbose_name='etherpad')),
                ('create_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
            ],
            options={
                'verbose_name': 'meetings_group',
                'verbose_name_plural': 'meetings_group',
                'db_table': 'meetings_group',
            },
        ),
        migrations.CreateModel(
            name='Record',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meeting_code', models.CharField(max_length=20, verbose_name='会议号')),
                ('file_size', models.CharField(max_length=20, verbose_name='视频大小')),
                ('download_url', models.CharField(max_length=255, verbose_name='下载地址')),
            ],
            options={
                'verbose_name': 'meetings_record',
                'verbose_name_plural': 'meetings_record',
                'db_table': 'meetings_record',
            },
        ),
        migrations.CreateModel(
            name='Meeting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('topic', models.CharField(max_length=128, verbose_name='会议主题')),
                ('community', models.CharField(blank=True, max_length=40, null=True, verbose_name='社区')),
                ('group_name', models.CharField(default='', max_length=40, verbose_name='组名')),
                ('group_type', models.SmallIntegerField(choices=[(1, 'SIG'), (2, 'MSG'), (3, 'Pro')], verbose_name='组别')),
                ('city', models.CharField(blank=True, max_length=10, null=True, verbose_name='城市')),
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
                ('password', models.CharField(blank=True, max_length=128, null=True, verbose_name='密码')),
                ('join_url', models.CharField(blank=True, max_length=128, null=True, verbose_name='进入会议url')),
                ('create_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
                ('is_delete', models.SmallIntegerField(choices=[(0, '否'), (1, '是')], default=0, verbose_name='是否删除')),
                ('meeting_type', models.SmallIntegerField(blank=True, choices=[(1, 'SIG'), (2, 'MSG'), (3, '专家委员会')], null=True, verbose_name='会议类型')),
                ('mmid', models.CharField(blank=True, max_length=20, null=True, verbose_name='腾讯会议id')),
                ('replay_url', models.CharField(blank=True, max_length=255, null=True, verbose_name='回放地址')),
                ('mplatform', models.CharField(blank=True, default='tencent', max_length=20, null=True, verbose_name='第三方会议平台')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='mindspore.group')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'meetings_meeting',
                'verbose_name_plural': 'meetings_meeting',
                'db_table': 'meetings_meeting',
            },
        ),
        migrations.CreateModel(
            name='GroupUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mindspore.group')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'meetings_groupuser',
                'verbose_name_plural': 'meetings_groupuser',
                'db_table': 'meetings_groupuser',
                'unique_together': {('group', 'user')},
            },
        ),
        migrations.CreateModel(
            name='Collect',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meeting', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mindspore.meeting')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'meetings_collect',
                'verbose_name_plural': 'meetings_collect',
                'db_table': 'meetings_collect',
                'unique_together': {('meeting', 'user')},
            },
        ),
        migrations.CreateModel(
            name='CityUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('city', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mindspore.city')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'meetings_cityuser',
                'verbose_name_plural': 'meetings_cityuser',
                'db_table': 'meetings_cityuser',
                'unique_together': {('city', 'user')},
            },
        ),
        migrations.CreateModel(
            name='ActivityCollect',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mindspore.activity')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'meetings_activitycollect',
                'verbose_name_plural': 'meetings_activitycollect',
                'db_table': 'meetings_activitycollect',
                'unique_together': {('activity', 'user')},
            },
        ),
    ]
