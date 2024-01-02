# -*- coding: utf-8 -*-
# @Time    : 2024/1/2 9:40
# @Author  : Tom_zc
# @FileName: utils.py
# @Software: PyCharm

import os
import json


def get_api(field: str) -> dict:
    """
    获取 API。

    Args:
        field (str): API 所属分类，即 data/api 下的文件名（不含后缀名）

    Returns:
        dict, 该 API 的内容。
    """
    path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "data", "api", f"{field.lower()}.json"
        )
    )
    if os.path.exists(path):
        with open(path, encoding="utf8") as f:
            return json.loads(f.read())
    else:
        return {}


def join(seperator: str, array: list):
    """
    用指定字符连接数组

    Args:
        seperator (str) : 分隔字符

        array     (list): 数组

    Returns:
        str: 连接结果
    """
    return seperator.join(map(lambda x: str(x), array))