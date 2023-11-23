# -*- coding: utf-8 -*-
# @Time    : 2023/10/25 10:14
# @Author  : Tom_zc
# @FileName: file_stream.py
# @Software: PyCharm
import stat
import os
import requests


def write_content(path, content, model="wb"):
    flags = os.O_CREAT | os.O_WRONLY
    modes = stat.S_IWUSR | stat.S_IRUSR
    with os.fdopen(os.open(path, flags, modes), model) as f:
        result = f.write(content)
    return result


def read_content(path):
    with open(path, 'r', encoding='utf-8') as fp:
        return fp.read()


def download_big_file(url, path, headers=None, model="wb"):
    if headers:
        r = requests.get(url, headers=headers, stream=True)
    else:
        r = requests.get(url, stream=True)
    flags = os.O_CREAT | os.O_WRONLY
    modes = stat.S_IWUSR | stat.S_IRUSR
    with os.fdopen(os.open(path, flags, modes), model) as f:
        for chunk in r.iter_content(chunk_size=4096):
            if chunk:
                f.write(chunk)
                f.flush()
    return path
