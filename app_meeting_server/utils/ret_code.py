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

    STATUS_FACILITY_BIT_MASK = 16
    STATUS_FACILITY_USER = 1 << STATUS_FACILITY_BIT_MASK
    STATUS_FACILITY_MEETING = 2 << STATUS_FACILITY_BIT_MASK
    STATUS_FACILITY_ACTIVITY = 3 << STATUS_FACILITY_BIT_MASK

    # sub module: users
    STATUS_USER = STATUS_FACILITY_USER + 0

    # sub module: meeting
    STATUS_MEETING = STATUS_FACILITY_MEETING + 0

    # sub module: activity
    STATUS_ACTIVITY = STATUS_FACILITY_ACTIVITY + 200

    EN_OPERATION = {
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
    }

    CN_OPERATION = {
        STATUS_SUCCESS: "操作成功",
        STATUS_PARTIAL_SUCCESS: "部分成功，请求数据可能不完整，请检查",
        STATUS_PARAMETER_ERROR: "参数无效",
        STATUS_FAILED: "失败",
        INTERNAL_ERROR: '内部错误，请稍后重试',
        SYSTEM_BUSY: '系统繁忙，请稍后重试',
        NAME_NOT_STANDARD: '非法名字',
        RESULT_IS_EMPTY: '结果为空',
        STATUS_PARAMETER_CORRESPONDING_ERROR: '参数响应无效',
        INFORMATION_CHANGE_ERROR: "信息已更改，请刷新后重试",

    }
