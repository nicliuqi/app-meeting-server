import datetime


def prepare(start_date, end_date, activity_category, activity_type, address, detail_address, register_method,
            register_url):
    if start_date > end_date:
        return {'code': 400, 'msg': ''}
    if start_date < (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d'):
        return {'code': 400, 'msg': '请最早提前一天申请活动'}
    if activity_category not in range(1, 5):
        return {'code': 400, 'msg': 'activity_category must be in 1-4'}
    if activity_type not in range(1, 4):
        return {'code': 400, 'msg': 'activity_type must be in 1-3'}
    if register_method == 2 and not register_url:
        return {'code': 400, 'msg': 'register_url is required to create the activity'}
