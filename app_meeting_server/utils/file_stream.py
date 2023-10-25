# -*- coding: utf-8 -*-
# @Time    : 2023/10/25 10:14
# @Author  : Tom_zc
# @FileName: file_stream.py
# @Software: PyCharm
import stat
import os


def write_content(path, content, model="wb"):
    flags = os.O_CREAT | os.O_WRONLY
    modes = stat.S_IWUSR
    with os.fdopen(os.open(path, flags, modes), model) as f:
        result = f.write(content)
    return result
