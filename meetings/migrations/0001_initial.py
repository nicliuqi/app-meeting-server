# Generated by Django 2.2.5 on 2020-08-06 15:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='GroupItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group_name', models.CharField(max_length=128, unique=True, verbose_name='组名')),
                ('description', models.CharField(max_length=255, verbose_name='组描述')),
                ('host_wechat_id', models.CharField(blank=True, max_length=128, null=True, verbose_name='主持人微信id')),
                ('host_email', models.CharField(blank=True, max_length=128, null=True, verbose_name='组主持人邮箱')),
                ('host_logo', models.CharField(blank=True, max_length=128, null=True, verbose_name='主持人头像logo')),
                ('etherpad', models.TextField(blank=True, null=True, verbose_name='etherpad')),
            ],
        ),
        migrations.CreateModel(
            name='LoginItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('wechat_id', models.CharField(max_length=128, unique=True, verbose_name='微信id')),
                ('login_type', models.CharField(max_length=20, verbose_name='登录类型')),
            ],
        ),
        migrations.CreateModel(
            name='MeetingItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meeting_id', models.CharField(blank=True, max_length=20, null=True, verbose_name='会议id')),
                ('topic', models.CharField(default=2, max_length=128, null=True, verbose_name='会议主题')),
                ('type', models.SmallIntegerField(choices=[(1, '紧急会议'), (2, '预定会议')], default=2, null=True, verbose_name='会议类型')),
                ('start_time', models.CharField(default=2, max_length=30, null=True, verbose_name='会议开始时间')),
                ('timezone', models.CharField(default=2, max_length=50, null=True, verbose_name='时区')),
                ('duration', models.IntegerField(default=2, null=True, verbose_name='持续时间')),
                ('group_id', models.CharField(blank=True, max_length=128, null=True)),
                ('password', models.CharField(blank=True, max_length=128, null=True, verbose_name='会议密码')),
                ('agenda', models.TextField(blank=True, null=True, verbose_name='议程')),
                ('etherpad', models.TextField(blank=True, null=True, verbose_name='etherpad')),
                ('zoom_host', models.EmailField(blank=True, max_length=254, null=True, verbose_name='主持人邮箱')),
                ('start_url', models.TextField(blank=True, null=True, verbose_name='开启会议url')),
                ('join_url', models.CharField(blank=True, max_length=128, null=True, verbose_name='进入会议url')),
            ],
        ),
        migrations.CreateModel(
            name='Repository',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='meetings.GroupItem', verbose_name='SIG组')),
            ],
        ),
        migrations.CreateModel(
            name='Maintainers',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='meetings.GroupItem', verbose_name='SIG组')),
            ],
        ),
        migrations.CreateModel(
            name='Email_list',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, verbose_name='受邀参会成员邮件')),
                ('meeting_id', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='meetings.MeetingItem', verbose_name='会议号')),
            ],
        ),
    ]
