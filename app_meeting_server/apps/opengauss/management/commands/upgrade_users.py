import binascii
from django.core.management.base import BaseCommand
from opengauss.models import User
from app_meeting_server.utils.common import encrypt_openid as encrypt, decrypt_openid as decrypt


class Command(BaseCommand):
    def handle(self, *args, **options):
        users = User.objects.all().values()
        for user in users:
            gitee_id = user.get('gitee_id')
            try:
                decrypt(gitee_id)
                continue
            except (binascii.Error, ValueError):
                encrypt_gitee_id = encrypt(gitee_id)
                User.objects.filter(gitee_id=gitee_id).update(gitee_id=encrypt_gitee_id)
