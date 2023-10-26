# -*- coding: utf-8 -*-
# @Time    : 2023/10/26 15:39
# @Author  : Tom_zc
# @FileName: ret_api.py
# @Software: PyCharm

from django.utils.encoding import force_str
from rest_framework import status
from rest_framework.exceptions import ErrorDetail, APIException
from django.utils.translation import gettext_lazy as _


class MyValidationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Invalid input.')
    default_code = 'invalid'

    def __init__(self, detail=None, code=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        text = force_str(detail)
        self.detail = ErrorDetail(text, code)
