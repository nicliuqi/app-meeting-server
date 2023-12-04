# -*- coding: utf-8 -*-
# @Time    : 2023/10/13 11:47
# @Author  : Tom_zc
# @FileName: common.py
# @Software: PyCharm
import secrets
import string
import subprocess
import threading
import time
import uuid
import tempfile
import os
import logging
import traceback
from contextlib import suppress
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import PBKDF2PasswordHasher
from django.conf import settings

from app_meeting_server.utils import crypto_gcm
from app_meeting_server.utils.file_stream import write_content
from app_meeting_server.utils.my_refresh import MyTokenObtainPairSerializer

logger = logging.getLogger('log')


def start_thread(func, m, record):
    th = threading.Thread(target=func, args=(m, record))
    th.start()


def get_cur_date():
    cur_date = datetime.now()
    return cur_date


def format_strptime(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d')


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


def make_refresh_signature(refresh_token):
    pbkdf2_password_hasher = PBKDF2PasswordHasher()
    return pbkdf2_password_hasher.encode(refresh_token, settings.REFRESH_SIGNATURE_SECRET, iterations=260000)


def refresh_access(user):
    refresh = MyTokenObtainPairSerializer.get_token(user)
    access_token = str(refresh.access_token)
    access_signature = make_signature(access_token)
    user_model = get_user_model()
    user_model.objects.filter(id=user.id).update(signature=access_signature)
    return access_token


def save_token(access_token, refresh_token, user):
    access_signature = make_signature(access_token)
    refresh_signature = make_refresh_signature(refresh_token)
    user_model = get_user_model()
    user_model.objects.filter(id=user.id).update(signature=access_signature, refresh_signature=refresh_signature)


def refresh_token_and_refresh_token(user):
    refresh = MyTokenObtainPairSerializer.get_token(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)
    save_token(access_token, refresh_token, user)
    return access_token, refresh_token


def clear_token(user):
    user_model = get_user_model()
    user_model.objects.filter(id=user.id).update(signature="", refresh_signature="")


def encrypt_openid(encrypt_openid):
    return crypto_gcm.aes_gcm_encrypt(encrypt_openid, settings.AES_GCM_SECRET, settings.AES_GCM_IV)


def decrypt_openid(decrypt_openid):
    return crypto_gcm.aes_gcm_decrypt(decrypt_openid, settings.AES_GCM_SECRET)


def gen_new_temp_dir():
    tmpdir = tempfile.gettempdir()
    while True:
        uuid_str = str(uuid.uuid4())
        new_uuid_str = uuid_str.replace("-", "")
        dir_name = os.path.join(tmpdir, new_uuid_str)
        if not os.path.exists(dir_name):
            return dir_name
        time.sleep(1)


def make_dir(path):
    if not os.path.exists(path):
        os.mkdir(path)


def save_temp_img(content):
    dir_name = gen_new_temp_dir()
    make_dir(dir_name)
    tmp_file = os.path.join(dir_name, 'tmp.jpeg')
    write_content(tmp_file, content, 'wb')
    return dir_name, tmp_file


def make_nonce():
    return ''.join(secrets.choice(string.digits) for _ in range(6))


def execute_cmd3(cmd, timeout=30, err_log=False):
    """execute cmd3"""
    try:
        p = subprocess.Popen(cmd.split(), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        t_wait_seconds = 0
        while True:
            if p.poll() is not None:
                break
            if timeout >= 0 and t_wait_seconds >= (timeout * 100):
                p.terminate()
                return -1, "", "execute_cmd3 exceeded time {} seconds in executing".format(timeout)
            time.sleep(0.01)
            t_wait_seconds += 1
        out, err = p.communicate()
        ret = p.returncode
        if ret != 0 and err_log:
            logger.error("execute_cmd3 return {}, std output: {}, err output: {}.".format(ret, out, err))
        return ret, out, err
    except Exception as e:
        return -1, "", "execute_cmd3 exceeded raise, e={}, trace={}".format(str(e), traceback.format_exc())


def get_date_by_start_and_end(start_date_str, end_date_str):
    all_date_list = list()
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    date_delta = (end_date - start_date).days
    if date_delta <= 0:
        return all_date_list
    for day in range(0, date_delta + 1):
        cur_date = start_date + timedelta(days=day)
        cur_date_str = cur_date.strftime("%Y-%m-%d")
        all_date_list.append(cur_date_str)
    return all_date_list


def get_version_params():
    return settings.PRIVACY_POLICY_VERSION, settings.PRIVACY_APP_POLICY_VERSION, get_cur_date()
