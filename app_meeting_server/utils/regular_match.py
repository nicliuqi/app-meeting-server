# -*- coding: utf-8 -*-
# @Time    : 2023/10/25 10:45
# @Author  : Tom_zc
# @FileName: regular_match.py
# @Software: PyCharm
import re


def match_email(email_str):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email_str) is not None
