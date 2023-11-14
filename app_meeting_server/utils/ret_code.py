# -*- coding: utf-8 -*-
# @Time    : 2023/10/26 18:52
# @Author  : Tom_zc
# @FileName: ret_code.py
# @Software: PyCharm


def _is_en(): return False


class RetCodeBase:
    EN_OPERATION = dict()
    CN_OPERATION = dict()

    @classmethod
    def get_name_by_code(cls, code):
        if _is_en():
            return cls.EN_OPERATION.get(code)
        else:
            return cls.CN_OPERATION.get(code)

    @classmethod
    def get_code_by_name(cls, name):
        if _is_en():
            temp = {value: key for key, value in cls.EN_OPERATION.items()}
            return temp.get(name, str())
        else:
            temp = {value: key for key, value in cls.CN_OPERATION.items()}
            return temp.get(name, str())


class RetCode(RetCodeBase):
    # common
    STATUS_SUCCESS = 0
    STATUS_PARAMETER_ERROR = -1
    STATUS_PARTIAL_SUCCESS = -2
    INTERNAL_ERROR = -3
    SYSTEM_BUSY = -4
    NAME_NOT_STANDARD = -5
    RESULT_IS_EMPTY = -6
    STATUS_PARAMETER_CORRESPONDING_ERROR = -7
    STATUS_FAILED = -8
    INFORMATION_CHANGE_ERROR = -9
    STATUS_START_LT_END = -10
    STATUS_START_GT_NOW = -11
    STATUS_START_LT_LIMIT = -12
    STATUS_START_VALID_URL = -13
    STATUS_START_VALID_XSS = -14
    STATUS_START_VALID_CRLF = -15

    STATUS_FACILITY_BIT_MASK = 16
    STATUS_FACILITY_USER = 1 << STATUS_FACILITY_BIT_MASK
    STATUS_FACILITY_MEETING = 2 << STATUS_FACILITY_BIT_MASK
    STATUS_FACILITY_ACTIVITY = 3 << STATUS_FACILITY_BIT_MASK

    # sub module: users
    STATUS_USER_HAS_SIGNED_POLICY = STATUS_FACILITY_USER + 0
    STATUS_SIG_GROUP_NOT_EXIST = STATUS_FACILITY_USER + 1
    STATUS_USER_HAS_NO_PERMISSIONS = STATUS_FACILITY_USER + 2
    STATUS_USER_LOGIN_FAILED = STATUS_FACILITY_USER + 3
    STATUS_USER_GET_CODE_FAILED = STATUS_FACILITY_USER + 4
    STATUS_USER_GET_OPENID_FAILED = STATUS_FACILITY_USER + 5
    STATUS_START_ONLY_ONE_ADMIN = STATUS_FACILITY_USER + 6

    # sub module: meeting
    STATUS_MEETING_EMAIL_LIST_OVER_LIMIT = STATUS_FACILITY_MEETING + 0
    STATUS_MEETING_EMAIL_OVER_LIMIT = STATUS_FACILITY_MEETING + 1
    STATUS_MEETING_INVALID_EMAIL = STATUS_FACILITY_MEETING + 2
    STATUS_MEETING_INVALID_ETHERPAD = STATUS_FACILITY_MEETING + 3
    STATUS_MEETING_FAILED_CREATE = STATUS_FACILITY_MEETING + 4
    STATUS_MEETING_NO_AVAILABLE_HOST = STATUS_FACILITY_MEETING + 5
    STATUS_MEETING_DATE_CONFLICT = STATUS_FACILITY_MEETING + 6
    STATUS_MEETING_CANNNOT_BE_DELETE = STATUS_FACILITY_MEETING + 7

    # sub module: activity
    STATUS_ACTIVITY_DATA_GT_NOW = STATUS_FACILITY_ACTIVITY + 0

    EN_OPERATION = {
        # common
        STATUS_SUCCESS: "Successfully",
        STATUS_PARTIAL_SUCCESS: "Partially successful, data may be incomplete, please check the cluster for exceptions",
        STATUS_PARAMETER_ERROR: "Parameter invalid",
        STATUS_FAILED: "Failed",
        INTERNAL_ERROR: 'Internal Error, Please try again',
        SYSTEM_BUSY: 'The system is busy',
        NAME_NOT_STANDARD: 'name not standard',
        RESULT_IS_EMPTY: 'The result is empty',
        STATUS_PARAMETER_CORRESPONDING_ERROR: 'Parameter corresponding invalid',
        INFORMATION_CHANGE_ERROR: "The information has changed, Please refresh and try again",
        STATUS_START_LT_END: "The start time should not be later than the end time",
        STATUS_START_GT_NOW: "The start time should not be later than the current time",
        STATUS_START_LT_LIMIT: "The start time is at most 60 days later than the current time",
        STATUS_START_VALID_URL: "Please do not enter URL links",
        STATUS_START_VALID_XSS: "Please do not enter XSS tags",
        STATUS_START_VALID_CRLF: "Please do not enter \r\n tags",

        # user
        STATUS_USER_HAS_SIGNED_POLICY: "The user has signed privacy policy agreement already.",
        STATUS_SIG_GROUP_NOT_EXIST: "The Group is not exist",
        STATUS_USER_HAS_NO_PERMISSIONS: "User has no access to delete meeting",
        STATUS_USER_LOGIN_FAILED: "User login failed",
        STATUS_USER_GET_CODE_FAILED: "Failed to get code",
        STATUS_USER_GET_OPENID_FAILED: "Failed to get openid",
        STATUS_START_ONLY_ONE_ADMIN: "There is only one administrator and cannot log out.",

        # meetings
        STATUS_MEETING_EMAIL_LIST_OVER_LIMIT: "The length of email_list is gt 600",
        STATUS_MEETING_EMAIL_OVER_LIMIT: "The length of email is gt 50",
        STATUS_MEETING_INVALID_EMAIL: "Invalid email address",
        STATUS_MEETING_INVALID_ETHERPAD: "Invalid etherpad",
        STATUS_MEETING_FAILED_CREATE: "Failed to create meeting",
        STATUS_MEETING_NO_AVAILABLE_HOST: "There is currently no available host, please go to the official website to view scheduled meetings",
        STATUS_MEETING_DATE_CONFLICT: "Time conflict, please adjust the time to schedule the meeting",
        STATUS_MEETING_CANNNOT_BE_DELETE: "Cannot be deleted 1 day before the meeting",

        # activity
        STATUS_ACTIVITY_DATA_GT_NOW: "The start date should be earlier than tomorrow"
    }

    CN_OPERATION = {
        # common
        STATUS_SUCCESS: "操作成功",
        STATUS_PARTIAL_SUCCESS: "部分成功，请求数据可能不完整，请检查",
        STATUS_PARAMETER_ERROR: "参数无效",
        STATUS_FAILED: "操作失败",
        INTERNAL_ERROR: '内部错误，请稍后重试',
        SYSTEM_BUSY: '系统繁忙，请稍后重试',
        NAME_NOT_STANDARD: '非法名字',
        RESULT_IS_EMPTY: '结果为空',
        STATUS_PARAMETER_CORRESPONDING_ERROR: '参数响应无效',
        INFORMATION_CHANGE_ERROR: "信息发生变化，请刷新后重试",
        STATUS_START_LT_END: "开始时间应小于结束时间",
        STATUS_START_GT_NOW: "开始时间应大于当前时间",
        STATUS_START_LT_LIMIT: "建议预定60天之内的会议或者活动",
        STATUS_START_VALID_URL: "请勿输入URL链接，XSS标签等内容",
        STATUS_START_VALID_XSS: "请勿输入XSS标签等内容",
        STATUS_START_VALID_CRLF: "请勿输入\r\n等内容",

        # user
        STATUS_USER_HAS_SIGNED_POLICY: "用户已签署隐私政策协议",
        STATUS_SIG_GROUP_NOT_EXIST: "用户组不存在",
        STATUS_USER_HAS_NO_PERMISSIONS: "无权限删除会议",
        STATUS_USER_LOGIN_FAILED: "用户登录失败",
        STATUS_USER_GET_CODE_FAILED: "获取code失败",
        STATUS_USER_GET_OPENID_FAILED: "获取openid失败",
        STATUS_START_ONLY_ONE_ADMIN: "管理员当前只有一个,无法注销.",

        # meetings
        STATUS_MEETING_EMAIL_LIST_OVER_LIMIT: "邮件地址长度超限",
        STATUS_MEETING_EMAIL_OVER_LIMIT: "单封邮件地址长度超限",
        STATUS_MEETING_INVALID_EMAIL: "无效的邮件地址",
        STATUS_MEETING_INVALID_ETHERPAD: "无效的Etherpad链接",
        STATUS_MEETING_FAILED_CREATE: "创建会议失败",
        STATUS_MEETING_NO_AVAILABLE_HOST: "目前没有可用的主持人，请前往官网查看预约会议",
        STATUS_MEETING_DATE_CONFLICT: "时间冲突，请调整时间预定会议",
        STATUS_MEETING_CANNNOT_BE_DELETE: "距离会议开始只有一天，无法删除",

        # activity
        STATUS_ACTIVITY_DATA_GT_NOW: "建议发布活动日期应该大于今天"

    }
