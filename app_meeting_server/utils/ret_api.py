# -*- coding: utf-8 -*-
# @Time    : 2023/10/26 15:39
# @Author  : Tom_zc
# @FileName: ret_api.py
# @Software: PyCharm
import logging
from functools import wraps
from django.http import JsonResponse
from django.utils.encoding import force_str
from rest_framework import status
from rest_framework.exceptions import ErrorDetail, APIException
from django.utils.translation import gettext_lazy as _

from app_meeting_server.utils.common import refresh_access
from app_meeting_server.utils.ret_code import RetCode

logger = logging.getLogger('log')


class MyValidationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Invalid input.')
    default_code = 'invalid'

    def __init__(self, detail=None, code=None):
        if isinstance(detail, int):
            detail = RetCode.get_name_by_code(detail)
        elif detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        text = force_str(detail)
        self.detail = ErrorDetail(text, code)


def ret_json(code=200, msg="success", data=None, access=None, **kwargs):
    ret_dict = {'code': code, 'msg': msg, "data": data}
    if access:
        ret_dict["access"] = access
    ret_dict.update(kwargs)
    return JsonResponse(ret_dict)


def ret_access_json(user, code=200, msg="success", data=None, **kwargs):
    access = refresh_access(user)
    ret_dict = {'code': code, 'msg': msg, "data": data, "access": access}
    ret_dict.update(kwargs)
    return JsonResponse(ret_dict)


def capture_myvalidation_exception(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except MyValidationError as e:
            logger.error("capture_myvalidation_exception:{} e:{}".format(fn.__name__, e))
            raise e
        except Exception as e:
            logger.error("capture_myvalidation_exception:{} e:{}".format(fn.__name__, e))

    return inner
