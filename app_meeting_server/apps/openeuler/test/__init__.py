#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/11/8 21:36
# @Author  : TomNewChao
# @File    : __init__.py.py
# @Description :


class PatchMock(object):
    def __init__(self, obj, func_name, target_func):
        super(PatchMock, self).__init__()
        self.obj = obj
        self.__name__ = func_name
        self.target_func = target_func

    def __enter__(self):
        self.origin_func = self.obj.__dict__.get(self.__name__)
        setattr(self.obj, self.__name__, self.target_func)

    def __exit__(self, exc_type, exc_val, exc_tb):
        setattr(self.obj, self.__name__, self.origin_func)
