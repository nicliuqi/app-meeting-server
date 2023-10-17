# -*- coding: utf-8 -*-
# @Time    : 2023/10/13 11:47
# @Author  : Tom_zc
# @FileName: common.py
# @Software: PyCharm
import pytz
import uuid
from contextlib import suppress
from datetime import datetime
from django.contrib.auth import get_user_model


def get_cur_date():
    tzinfo = pytz.timezone('Asia/Shanghai')
    cur_date = datetime.now(tz=tzinfo)
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
