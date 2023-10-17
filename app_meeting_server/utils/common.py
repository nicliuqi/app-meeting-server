# -*- coding: utf-8 -*-
# @Time    : 2023/10/13 11:47
# @Author  : Tom_zc
# @FileName: common.py
# @Software: PyCharm
import pytz
import uuid
from contextlib import suppress
from datetime import datetime


def get_cur_date():
    tzinfo = pytz.timezone('Asia/Shanghai')
    cur_date = datetime.now(tz=tzinfo)
    return cur_date


def get_uuid(self):
    while True:
        uid = uuid.uuid4()
        res = str(uid).split('-')[0]
        with suppress(ValueError):
            self.check_unique(uid)
        return 'USER_{}'.format(res)