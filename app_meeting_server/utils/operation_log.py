# -*- coding: utf-8 -*-
# @Time    : 2023/10/11 16:09
# @Author  : Tom_zc
# @FileName: operation_log.py
# @Software: PyCharm
import json

from django.conf import settings
from logging import getLogger
from functools import wraps
from rest_framework.response import Response
from django.http import JsonResponse

logger = getLogger("django")

logger_template = "(Client ip:{}, User id:{}, Module:{},Type:{})Desc:{},Result:{}."


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
    OP_MODULE_CITY = 3

    CN_OPERATION = {
        OP_MODULE_USER: "用户",
        OP_MODULE_MEETING: "会议",
        OP_MODULE_ACTIVITY: "活动",
        OP_MODULE_CITY: "城市",
    }

    EN_OPERATION = {
        OP_MODULE_USER: "user",
        OP_MODULE_MEETING: "meeting",
        OP_MODULE_ACTIVITY: "activity",
        OP_MODULE_CITY: "city",
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
    OP_TYPE_LOGOFF = 8
    OP_TYPE_COLLECT = 9
    OP_TYPE_CANCEL_COLLECT = 10

    CN_OPERATION = {
        OP_TYPE_LOGIN: "登录",
        OP_TYPE_LOGOUT: "登出",
        OP_TYPE_LOGOFF: "注销",
        OP_TYPE_CREATE: "新建",
        OP_TYPE_DELETE: "删除",
        OP_TYPE_QUERY: "查询",
        OP_TYPE_MODIFY: "修改",
        OP_TYPE_EXPORT: "导出",
        OP_TYPE_DOWNLOAD: "下载",
        OP_TYPE_COLLECT: "收藏",
        OP_TYPE_CANCEL_COLLECT: "取消收藏",
    }

    EN_OPERATION = {
        OP_TYPE_LOGIN: "login",
        OP_TYPE_LOGOUT: "logout",
        OP_TYPE_LOGOFF: "logoff",
        OP_TYPE_CREATE: "create",
        OP_TYPE_DELETE: "delete",
        OP_TYPE_QUERY: "query",
        OP_TYPE_MODIFY: "modify",
        OP_TYPE_EXPORT: "export",
        OP_TYPE_DOWNLOAD: "download",
        OP_TYPE_COLLECT: "collect",
        OP_TYPE_CANCEL_COLLECT: "cancel collect",
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
    # City CODE START 3000
    OP_DESC_USER_BASE_CODE = 0
    OP_DESC_USER_LOGIN_CODE = OP_DESC_USER_BASE_CODE + 1
    OP_DESC_USER_LOGOUT_CODE = OP_DESC_USER_BASE_CODE + 2
    OP_DESC_USER_LOGOFF_CODE = OP_DESC_USER_BASE_CODE + 3
    OP_DESC_USER_MODIIFY_CODE = OP_DESC_USER_BASE_CODE + 4
    OP_DESC_USER_ADD_GROUP_CODE = OP_DESC_USER_BASE_CODE + 5
    OP_DESC_USER_REMOVE_GROUP_CODE = OP_DESC_USER_BASE_CODE + 6
    OP_DESC_USER_ADD_ACTIVITY_SPONSOR_CODE = OP_DESC_USER_BASE_CODE + 7
    OP_DESC_USER_REMOVE_ACTIVITY_SPONSOR_CODE = OP_DESC_USER_BASE_CODE + 8
    OP_DESC_USER_AGREEMENT_CODE = OP_DESC_USER_BASE_CODE + 9
    OP_DESC_USER_REVOKEAGREEMENT_CODE = OP_DESC_USER_BASE_CODE + 10

    OP_DESC_MEETING_BASE_CODE = 1000
    OP_DESC_MEETING_CREATE_CODE = OP_DESC_MEETING_BASE_CODE + 1
    OP_DESC_MEETING_DELETE_CODE = OP_DESC_MEETING_BASE_CODE + 2
    OP_DESC_MEETING_COLLECT_CODE = OP_DESC_MEETING_BASE_CODE + 3
    OP_DESC_MEETING_CANCEL_COLLECT_CODE = OP_DESC_MEETING_BASE_CODE + 4
    OP_DESC_MEETING_MODIFY_CODE = OP_DESC_MEETING_BASE_CODE + 5

    OP_DESC_ACTIVITY_BASE_CODE = 2000
    OP_DESC_ACTIVITY_CREATE_CODE = OP_DESC_ACTIVITY_BASE_CODE + 1
    OP_DESC_ACTIVITY_MODIFY_CODE = OP_DESC_ACTIVITY_BASE_CODE + 2
    OP_DESC_ACTIVITY_PUBLISH_PASS_CODE = OP_DESC_ACTIVITY_BASE_CODE + 3
    OP_DESC_ACTIVITY_PUBLISH_REJECT_CODE = OP_DESC_ACTIVITY_BASE_CODE + 4
    OP_DESC_ACTIVITY_DELETE_CODE = OP_DESC_ACTIVITY_BASE_CODE + 5
    OP_DESC_ACTIVITY_CREATE_DRAFT_CODE = OP_DESC_ACTIVITY_BASE_CODE + 6
    OP_DESC_ACTIVITY_DELETE_DRAFT_CODE = OP_DESC_ACTIVITY_BASE_CODE + 7
    OP_DESC_ACTIVITY_MODIFY_DRAFT_CODE = OP_DESC_ACTIVITY_BASE_CODE + 8
    OP_DESC_ACTIVITY_PUBLISH_DRAFT_CODE = OP_DESC_ACTIVITY_BASE_CODE + 9
    OP_DESC_ACTIVITY_COLLECT_CODE = OP_DESC_ACTIVITY_BASE_CODE + 10
    OP_DESC_ACTIVITY_CANCEL_COLLECT_CODE = OP_DESC_ACTIVITY_BASE_CODE + 11

    OP_DESC_CITY_BASE_CODE = 3000
    OP_DESC_CITY_CREATE_CODE = OP_DESC_CITY_BASE_CODE + 1
    OP_DESC_CITY_ADD_USER_CODE = OP_DESC_CITY_BASE_CODE + 2
    OP_DESC_CITY_REMOVE_USER_CODE = OP_DESC_CITY_BASE_CODE + 3

    CN_OPERATION = {
        # user
        OP_DESC_USER_LOGIN_CODE: "用户登录。",
        OP_DESC_USER_LOGOUT_CODE: "用户（%s）登出。",
        OP_DESC_USER_LOGOFF_CODE: "用户（%s）注销。",
        OP_DESC_USER_MODIIFY_CODE: "用户（%s）修改用户（%s）信息。",
        OP_DESC_USER_ADD_GROUP_CODE: "用户（%s）被添加到SIG组（%s）。",
        OP_DESC_USER_REMOVE_GROUP_CODE: "用户（%s）从SIG组（%s）中移除。",
        OP_DESC_USER_ADD_ACTIVITY_SPONSOR_CODE: "用户（%s）被添加为活动发起人。",
        OP_DESC_USER_REMOVE_ACTIVITY_SPONSOR_CODE: "用户（%s）从活动发起人中移除。",
        OP_DESC_USER_AGREEMENT_CODE: "用户（%s）同意隐私声明。",
        OP_DESC_USER_REVOKEAGREEMENT_CODE: "用户（%s）撤销隐私声明。",


        # meeting
        OP_DESC_MEETING_CREATE_CODE: "创建会议（%s）。",
        OP_DESC_MEETING_DELETE_CODE: "删除会议（%s）。",
        OP_DESC_MEETING_COLLECT_CODE: "收藏会议（%s）。",
        OP_DESC_MEETING_CANCEL_COLLECT_CODE: "取消收藏会议（%s）。",
        OP_DESC_MEETING_MODIFY_CODE: "修改会议（%s）。",

        # activity
        OP_DESC_ACTIVITY_CREATE_CODE: "创建活动（%s）。",
        OP_DESC_ACTIVITY_MODIFY_CODE: "修改活动（%s）。",
        OP_DESC_ACTIVITY_PUBLISH_PASS_CODE: "成功发布活动（%s）。",
        OP_DESC_ACTIVITY_PUBLISH_REJECT_CODE: "驳回发布活动的申请（%s）。",
        OP_DESC_ACTIVITY_DELETE_CODE: "删除活动（%s）。",
        OP_DESC_ACTIVITY_CREATE_DRAFT_CODE: "创建活动草案（%s）。",
        OP_DESC_ACTIVITY_DELETE_DRAFT_CODE: "删除活动草案（%s）。",
        OP_DESC_ACTIVITY_MODIFY_DRAFT_CODE: "修改活动草案（%s）。",
        OP_DESC_ACTIVITY_PUBLISH_DRAFT_CODE: "修改活动草案并发布（%s）。",
        OP_DESC_ACTIVITY_COLLECT_CODE: "收藏活动（%s）。",
        OP_DESC_ACTIVITY_CANCEL_COLLECT_CODE: "取消收藏活动（%s）。",

        # city
        OP_DESC_CITY_CREATE_CODE: "创建城市（%s）。",
        OP_DESC_CITY_ADD_USER_CODE: "城市（%s）添加用户（%s）。",
        OP_DESC_CITY_REMOVE_USER_CODE: "城市（%s）移除用户（%s）。",

    }

    EN_OPERATION = {
        # user
        OP_DESC_USER_LOGIN_CODE: "The user login.",
        OP_DESC_USER_LOGOUT_CODE: "The user(%s) logout.",
        OP_DESC_USER_LOGOFF_CODE: "The user(%s) logoff.",
        OP_DESC_USER_MODIIFY_CODE: "The user(%s) modify the user(%s) info.",
        OP_DESC_USER_ADD_GROUP_CODE: "The user(%s) is added to SIG group(%s).",
        OP_DESC_USER_REMOVE_GROUP_CODE: "The user(%s) is removed from SIG group(%s).",
        OP_DESC_USER_ADD_ACTIVITY_SPONSOR_CODE: "The user(%s) was added as activity sponsor.",
        OP_DESC_USER_REMOVE_ACTIVITY_SPONSOR_CODE: "The user(%s) was removed from activity sponsor.",
        OP_DESC_USER_AGREEMENT_CODE: "The user(%s) agree to privacy statement.",
        OP_DESC_USER_REVOKEAGREEMENT_CODE: "The user(%s) revokes privacy statement.",

        # meeting
        OP_DESC_MEETING_CREATE_CODE: "Create meeting(%s).",
        OP_DESC_MEETING_DELETE_CODE: "Delete meeting(%s).",
        OP_DESC_MEETING_COLLECT_CODE: "Collect meeting(%s).",
        OP_DESC_MEETING_CANCEL_COLLECT_CODE: "Cancel to collect meeting(%s).",
        OP_DESC_MEETING_MODIFY_CODE: "Modify meeting(%s).",

        # activity
        OP_DESC_ACTIVITY_CREATE_CODE: "Create activity(%s).",
        OP_DESC_ACTIVITY_MODIFY_CODE: "Modify activity(%s).",
        OP_DESC_ACTIVITY_PUBLISH_PASS_CODE: "Pass to publish activity(%s).",
        OP_DESC_ACTIVITY_PUBLISH_REJECT_CODE: "Reject to publish activity(%s).",
        OP_DESC_ACTIVITY_DELETE_CODE: "Delete activity(%s).",
        OP_DESC_ACTIVITY_CREATE_DRAFT_CODE: "Create the activity draft(%s).",
        OP_DESC_ACTIVITY_DELETE_DRAFT_CODE: "Delete the activity draft(%s).",
        OP_DESC_ACTIVITY_MODIFY_DRAFT_CODE: "Modify the activity draft(%s).",
        OP_DESC_ACTIVITY_PUBLISH_DRAFT_CODE: "Modifies the activity draft and publishes it(%s).",
        OP_DESC_ACTIVITY_COLLECT_CODE: "Collect the activity(%s).",
        OP_DESC_ACTIVITY_CANCEL_COLLECT_CODE: "Cancel to collect the activity(%s).",

        # city
        OP_DESC_CITY_CREATE_CODE: "Create city(%s).",
        OP_DESC_CITY_ADD_USER_CODE: "City(%s) add user(%s).",
        OP_DESC_CITY_REMOVE_USER_CODE: "City(%s) remove user(%s).",

    }


def console_log(request, log_module, log_desc, log_type, log_vars, resp=None):
    ip = request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR")
    user_id = "anonymous" if not request.user.id else str(request.user.id)
    result = OperationLogResult.OP_RESULT_FAILED
    if isinstance(resp, Response) and str(resp.status_code).startswith("20"):
        result = OperationLogResult.OP_RESULT_SUCCEED
    elif isinstance(resp, JsonResponse):
        json_data = json.loads(resp.content)
        if str(json_data.get("code")).startswith("20"):
            result = OperationLogResult.OP_RESULT_SUCCEED
    elif resp:
        result = OperationLogResult.OP_RESULT_SUCCEED
    log_module_str = OperationLogModule.get_name_by_code(log_module)
    log_type_str = OperationLogType.get_name_by_code(log_type)
    log_desc_str = OperationLogDesc.get_name_by_code(log_desc)
    log_result_str = OperationLogResult.get_name_by_code(result)
    log_vars_tuple = tuple() if log_vars is None else tuple(log_vars)
    log_detail = log_desc_str % log_vars_tuple
    msg = logger_template.format(ip, user_id, log_module_str, log_type_str, log_detail, log_result_str)
    logger.info(msg)


class LoggerContext:
    def __init__(self, request, log_module, log_type, log_desc):
        self.request = request
        self.log_module = log_module
        self.log_type = log_type
        self.log_desc = log_desc
        self.log_vars = list()
        self.result = None

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        console_log(self.request, self.log_module, self.log_desc, self.log_type, self.log_vars, self.result)


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
