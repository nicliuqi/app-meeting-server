# -*- coding: utf-8 -*-
# @Time    : 2023/11/14 16:37
# @Author  : Tom_zc
# @FileName: common.py
# @Software: PyCharm
from app_meeting_server.utils.common import encrypt_openid, make_refresh_signature
from openeuler.models import User


def create_user(username, openid, refresh):
    encrypt_openid_str = encrypt_openid(openid)
    refresh_signature = make_refresh_signature(refresh)
    User.objects.create(
        nickname=username,
        avatar="https://xxxxxxx",
        openid=encrypt_openid_str,
        refresh_signature=refresh_signature)
