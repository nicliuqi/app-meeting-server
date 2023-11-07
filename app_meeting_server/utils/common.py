# -*- coding: utf-8 -*-
# @Time    : 2023/10/13 11:47
# @Author  : Tom_zc
# @FileName: common.py
# @Software: PyCharm
import secrets
import string
import subprocess
import time
import uuid
import tempfile
import os
import logging
import traceback
from contextlib import suppress
from datetime import datetime
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import PBKDF2PasswordHasher
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from app_meeting_server.utils import crypto_gcm
from app_meeting_server.utils.file_stream import write_content

logger = logging.getLogger('log')


def get_cur_date():
    cur_date = datetime.now()
    return cur_date


def check_unique(uid):
    user_model = get_user_model()
    if user_model.objects.filter(nickname='USER_{}'.format(uid)):
        raise ValueError('Duplicate nickname')
    return 'USER_{}'.format(uid)


def get_uuid():
    while True:
        uid = uuid.uuid4()
        res = str(uid).split('-')[0]
        with suppress(ValueError):
            check_unique(uid)
        return 'USER_{}'.format(res)


def make_signature(access_token):
    pbkdf2_password_hasher = PBKDF2PasswordHasher()
    return pbkdf2_password_hasher.encode(access_token, settings.SIGNATURE_SECRET, iterations=260000)


def refresh_access(user):
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    encrypt_access = make_signature(access)
    user_model = get_user_model()
    user_model.objects.filter(id=user.id).update(signature=encrypt_access)
    return access


def encrypt_openid(encrypt_openid):
    return crypto_gcm.aes_gcm_encrypt(encrypt_openid, settings.AES_GCM_SECRET, settings.AES_GCM_IV)


def decrypt_openid(decrypt_openid):
    return crypto_gcm.aes_gcm_decrypt(decrypt_openid, settings.AES_GCM_SECRET)


def save_temp_img(content):
    tmpdir = tempfile.gettempdir()
    tmp_file = os.path.join(tmpdir, 'tmp.jpeg')
    write_content(tmp_file, content, 'wb')
    return tmp_file


def make_nonce():
    return ''.join(secrets.choice(string.digits) for _ in range(6))


def execute_cmd3(cmd, timeout=30, err_log=True):
    """execute cmd3"""
    try:
        logger.info("execute_cmd3 call cmd: {}".format(cmd))
        p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        t_wait_seconds = 0
        while True:
            if p.poll() is not None:
                break
            if timeout >= 0 and t_wait_seconds >= (timeout * 100):
                p.terminate()
                return -1, "", "execute_cmd3 exceeded time {} seconds in executing: {}".format(timeout, cmd)
            time.sleep(0.01)
            t_wait_seconds += 1
        out, err = p.communicate()
        ret = p.returncode
        if ret != 0 and err_log:
            logger.error("execute_cmd3 cmd {} return {}, std output: {}, err output: {}.".format(cmd, ret, out, err))
        return ret, out, err
    except Exception as e:
        return -1, "", "execute_cmd3 exceeded raise, e={}, trace={}".format(e.args[0], traceback.format_exc())

