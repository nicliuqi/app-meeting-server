# Generated by Django 2.2.28 on 2023-11-17 14:29

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('openeuler', '0004_user_refresh_signature'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='agree_privacy_app_policy_version',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='同意隐私政策应用版本'),
        ),
    ]
