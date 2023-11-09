# -*- coding: utf-8 -*-
# @Time    : 2023/10/25 10:45
# @Author  : Tom_zc
# @FileName: regular_match.py
# @Software: PyCharm
import re

email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
url_pattern = re.compile(r'https://|http://|www\.')
crlf_pattern = re.compile(r'\r|\n|\r\n')


def match_email(email_str):
    return email_pattern.match(email_str) is not None


def match_url(url_str):
    return url_pattern.findall(url_str)


def match_crlf(content):
    return crlf_pattern.findall(content)
