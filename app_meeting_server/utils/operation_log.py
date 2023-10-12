# -*- coding: utf-8 -*-
# @Time    : 2023/10/11 16:09
# @Author  : Tom_zc
# @FileName: operation_log.py
# @Software: PyCharm

from django.conf import settings
from logging import getLogger
from functools import wraps
from rest_framework.response import Response
from django.http import JsonResponse

logger = getLogger("django")

logger_template = "[operation log] Client ip:{}, User id:{}, Module:{},Type:{},Desc:{},Result:{}."


def is_en(): return settings.LANGUAGE_CODE == 'en-us'


class OperationBase:
    @classmethod
    def get_name_by_code(cls, code):
        if is_en():
            return cls.EN_OPERATION.get(code)
        else:
            return cls.CN_OPERATION.get(code)

    @classmethod
    def get_code_by_name(cls, name):
        if is_en():
            temp = {value: key for key, value in cls.EN_OPERATION.items()}
            return temp.get(name, str())
        else:
            temp = {value: key for key, value in cls.CN_OPERATION.items()}
            return temp.get(name, str())


class OperationLogModule(OperationBase):
    OP_MODULE_USER = 0
    OP_MODULE_MEETING = 1
    OP_MODULE_ACTIVITY = 2

    CN_OPERATION = {
        OP_MODULE_USER: "用户",
        OP_MODULE_MEETING: "会议",
        OP_MODULE_ACTIVITY: "活动",
    }

    EN_OPERATION = {
        OP_MODULE_USER: "user",
        OP_MODULE_MEETING: "meeting",
        OP_MODULE_ACTIVITY: "activity",
    }


class OperationLogType(OperationBase):
    OP_TYPE_LOGIN = 0
    OP_TYPE_LOGOUT = 1
    OP_TYPE_CREATE = 2
    OP_TYPE_DELETE = 3
    OP_TYPE_QUERY = 4
    OP_TYPE_MODIFY = 5
    OP_TYPE_EXPORT = 6
    OP_TYPE_DOWNLOAD = 7

    CN_OPERATION = {
        OP_TYPE_LOGIN: "登录",
        OP_TYPE_LOGOUT: "登出",
        OP_TYPE_CREATE: "新建",
        OP_TYPE_DELETE: "删除",
        OP_TYPE_QUERY: "查询",
        OP_TYPE_MODIFY: "修改",
        OP_TYPE_EXPORT: "导出",
        OP_TYPE_DOWNLOAD: "下载",
    }

    EN_OPERATION = {
        OP_TYPE_LOGIN: "login",
        OP_TYPE_LOGOUT: "logout",
        OP_TYPE_CREATE: "create",
        OP_TYPE_DELETE: "delete",
        OP_TYPE_QUERY: "query",
        OP_TYPE_MODIFY: "modify",
        OP_TYPE_EXPORT: "export",
        OP_TYPE_DOWNLOAD: "download",
    }


class OperationLogResult(OperationBase):
    OP_RESULT_SUCCEED = 0
    OP_RESULT_FAILED = 1

    CN_OPERATION = {
        OP_RESULT_SUCCEED: "成功",
        OP_RESULT_FAILED: "失败",
    }

    EN_OPERATION = {
        OP_RESULT_SUCCEED: "succeed",
        OP_RESULT_FAILED: "failed"
    }


# noinspection PyTypeChecker
class OperationLogDesc(OperationBase):
    # USER CODE START 0
    # MEETING CODE START 1000
    # Activity CODE START 2000
    OP_DESC_USER_BASE_CODE = 0
    OP_DESC_USER_LOGIN_CODE = OP_DESC_USER_BASE_CODE + 1
    OP_DESC_USER_LOGOUT_CODE = OP_DESC_USER_BASE_CODE + 2

    OP_DESC_MEETING_BASE_CODE = 1000
    OP_DESC_MEETING_DEMO_CODE = OP_DESC_MEETING_BASE_CODE + 1

    OP_DESC_ACTIVITY_BASE_CODE = 2000
    OP_DESC_ACTIVITY_DEMO_CODE = OP_DESC_ACTIVITY_BASE_CODE + 1

    CN_OPERATION = {
        # user
        OP_DESC_USER_LOGIN_CODE: "用户登录",
        OP_DESC_USER_LOGOUT_CODE: "用户登出",

        # meeting
        OP_DESC_MEETING_DEMO_CODE: "会议（%s）demo",

        # activity
        OP_DESC_ACTIVITY_DEMO_CODE: "活动（%s）demo",

    }

    EN_OPERATION = {
        # user
        OP_DESC_USER_LOGIN_CODE: "The user login.",
        OP_DESC_USER_LOGOUT_CODE: "The user logout.",

        # meeting
        OP_DESC_MEETING_DEMO_CODE: "meeting（%s）demo",

        # activity
        OP_DESC_ACTIVITY_DEMO_CODE: "activity（%s）demo",

    }


def console_log(request, log_module, log_desc, log_type, log_vars, resp=None):
    ip = request.META.get("x-forward-for") or request.META.get("REMOTE_ADDR")
    user_id = "anonymous" if request.user.is_anonymous else str(request.user.id)
    result = OperationLogResult.OP_RESULT_FAILED
    if isinstance(resp, Response) and str(resp.status_code).startswith("20"):
        result = OperationLogResult.OP_RESULT_SUCCEED
    elif isinstance(resp, JsonResponse) and str(resp["code"]).startswith("20"):
        result = OperationLogResult.OP_RESULT_SUCCEED
    log_module_str = OperationLogModule.get_name_by_code(log_module)
    log_type_str = OperationLogType.get_name_by_code(log_type)
    log_desc_str = OperationLogDesc.get_name_by_code(log_desc)
    log_result_str = OperationLogResult.get_name_by_code(result)
    log_vars_tuple = tuple() if log_vars is None else tuple(log_vars)
    log_detail = log_desc_str % log_vars_tuple
    msg = logger_template.format(ip, user_id, log_module_str, log_type_str, log_detail, log_result_str)
    logger.info(msg)


def loggerwrapper(log_module, log_desc, log_type=None, log_vars=None):
    def wrapper(fn):
        @wraps(fn)
        def inner(view, request, *args, **kwargs):
            try:
                resp = fn(view, request, *args, **kwargs)
                console_log(request, log_module, log_desc, log_type, log_vars, resp)
                return resp
            except Exception as e:
                console_log(request, log_module, log_desc, log_type, log_vars)
                raise e

        return inner

    return wrapper

