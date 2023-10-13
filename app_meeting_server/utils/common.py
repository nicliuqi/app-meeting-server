# -*- coding: utf-8 -*-
# @Time    : 2023/10/13 11:47
# @Author  : Tom_zc
# @FileName: common.py
# @Software: PyCharm
import pytz
from datetime import datetime


def get_cur_date():
    tzinfo = pytz.timezone('Asia/Shanghai')
    cur_date = datetime.now(tz=tzinfo)
    return cur_date
