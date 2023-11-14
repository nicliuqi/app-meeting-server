import copy
import json

from rest_framework import status
from rest_framework.test import APITestCase
from openeuler.models import User, GroupUser, Meeting, Collect, Activity, ActivityCollect
from openeuler.test.common import create_user, create_group, create_meetings_sponsor_user, create_meeting_admin_user, \
    get_user, create_activity_sponsor_user, create_activity_admin_user

from openeuler.test.constant import xss_script, crlf_text, html_text


# noinspection PyUnresolvedReferences
class TestCommon(APITestCase):

    def test_without_token(self):
        ret = self.client.post(self.url)
        self.assertEqual(ret.status_code, status.HTTP_401_UNAUTHORIZED)

    def init_user(self, count_data=50):
        for i in range(count_data):
            create_user("username_{}".format(i), "openid_{}".format(i))

    def init_group(self, count_data=50):
        group = create_group("group_user")
        self.init_user(count_data)
        return group

    def init_meetings(self, data):
        group = create_group(data["group_name"])
        data["group_id"] = group.id
        header = create_meetings_sponsor_user("sponsor", "sponsor_openid")
        return header, data

    def tearDown(self) -> None:
        ret = GroupUser.objects.all().delete()
        logger.info("delete group user and result is:{}".format(str(ret)))
        ret = Meeting.objects.all().delete()
        logger.info("delete meeting and result is:{}".format(str(ret)))
        ret = Collect.objects.all().delete()
        logger.info("delete meeting collect and result is:{}".format(str(ret)))
        ret = Activity.objects.all().delete()
        logger.info("delete activity and result is:{}".format(str(ret)))
        ret = ActivityCollect.objects.all().delete()
        logger.info("delete activity collect and result is:{}".format(str(ret)))
        ret = User.objects.all().delete()
        logger.info("delete user and result is:{}".format(str(ret)))


class LoginViewTest(APITestCase):
    value = "*" * 16
    url = "/login/"

    def test_login_lack_openid(self):
        ret = self.client.post(self.url, data=dict())
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_invalid_openid(self):
        ret = self.client.post(self.url, data={"code": "*" * 129})
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_empty_openid(self):
        ret = self.client.post(self.url, data={"code": ""})
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)


class RefreshViewTest(APITestCase):
    url = "/refresh/"

    def test_refresh_lack_refresh(self):
        ret = self.client.post(self.url, data={})
        self.assertEqual(ret.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_not_match(self):
        ret = self.client.post(self.url, data={"refresh": "match"})
        self.assertEqual(ret.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_ok(self):
        _, refresh_token = create_user("test_refresh_ok", "test_refresh_ok")
        ret = self.client.post(self.url, data={"refresh": refresh_token})
        self.assertEqual(ret.status_code, status.HTTP_200_OK)

    def test_refresh_expired(self):
        """Need to test manually"""
        pass


class LogoutViewTest(TestCommon):
    url = "/logout/"

    def test_logout_ok(self):
        header, _ = create_user("test_logout_ok", "test_logout_ok")
        ret = self.client.post(self.url, hearder=header)
        self.assertEqual(ret.status_code, status.HTTP_200_OK)


class LogoffViewTest(TestCommon):
    url = "/logoff/"

    def test_logoff_ok(self):
        header, _ = create_user("test_logout_ok", "test_logout_ok")
        ret = self.client.post(self.url, hearder=header)
        self.assertEqual(ret.status_code, status.HTTP_200_OK)


class AgreePrivacyPolicyViewTest(TestCommon):
    url = "/agree/"

    def test_agree_privacy_ok(self):
        header, _ = create_user("test_logout_ok", "test_logout_ok")
        ret = self.client.post(self.url, hearder=header)
        self.assertEqual(ret.status_code, status.HTTP_200_OK)


class RevokeAgreementViewTest(TestCommon):
    url = "/revoke/"

    def test_revoke_agree_privacy_ok(self):
        header, _ = create_user("test_logout_ok", "test_logout_ok")
        ret = self.client.post(self.url, hearder=header)
        self.assertEqual(ret.status_code, status.HTTP_200_OK)


class GroupUserAddViewTest(TestCommon):
    url = "/groupuser/action/new/"
    data = {
        "group_id": "",
        "ids": "1-2"
    }

    def test_with_ok(self):
        group = create_group("group1")
        for i in range(50):
            create_user("username_{}".format(i), "openid_{}".format(i))
        header = create_meeting_admin_user("user_admin")
        self.data["group_id"] = group.id
        self.data["ids"] = "-".join(User.objects.values_list("id", flat=True))
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_200_OK)

    def test_over_user_count(self):
        group = create_group("group1")
        for i in range(51):
            create_user("username_{}".format(i), "openid_{}".format(i))
        header = create_meeting_admin_user("user_admin")
        self.data["group_id"] = group.id
        self.data["ids"] = "-".join(User.objects.values_list("id", flat=True))
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_count_eq_zero(self):
        group = create_group("group1")
        create_user("username_0", "openid_0")
        header = create_meeting_admin_user("user_admin")
        self.data["group_id"] = group.id
        self.data["ids"] = ""
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_count_not_eq_int(self):
        group = create_group("group1")
        create_user("username_0", "openid_0")
        user = User.objects.get(nickname="username_0")
        header = create_meeting_admin_user("user_admin")
        self.data["group_id"] = group.id
        self.data["ids"] = "{}-xxx".format(user.id)
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_group_not_exist(self):
        create_user("username_0", "openid_0")
        header = create_meeting_admin_user("user_admin")
        user = User.objects.get(nickname="username_0")
        self.data["group_id"] = str(1)
        self.data["ids"] = "{}".format(user.id)
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_permission(self):
        header = create_meetings_sponsor_user()
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_permission_2(self):
        header = create_user()
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)


class GroupUserDelViewTest(TestCommon):
    url = "/groupuser/action/del/"
    data = {
        "group_id": "",
        "ids": "1-2"
    }

    def test_with_ok(self):
        group = self.init_group()
        header = create_meeting_admin_user("user_admin")
        self.data["group_id"] = group.id
        self.data["ids"] = "-".join(User.objects.values_list("id", flat=True))
        self.client.post(GroupUserAddViewTest.url, hearder=header, data=GroupUserAddViewTest.data)
        header = get_user("user_admin")
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_200_OK)

    def test_over_user_count(self):
        group = create_group("group1")
        for i in range(51):
            create_user("username_{}".format(i), "openid_{}".format(i))
        header = create_meeting_admin_user("user_admin")
        self.data["group_id"] = group.id
        self.data["ids"] = "-".join(User.objects.values_list("id", flat=True))
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_count_eq_zero(self):
        group = create_group("group1")
        create_user("username_0", "openid_0")
        header = create_meeting_admin_user("user_admin")
        self.data["group_id"] = group.id
        self.data["ids"] = ""
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_count_not_eq_int(self):
        group = create_group("group1")
        create_user("username_0", "openid_0")
        user = User.objects.get(nickname="username_0")
        header = create_meeting_admin_user("user_admin")
        self.data["group_id"] = group.id
        self.data["ids"] = "{}-xxx".format(user.id)
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_group_not_exist(self):
        create_user("username_0", "openid_0")
        user = User.objects.get(nickname="username_0")
        header = create_meeting_admin_user("user_admin")
        self.data["group_id"] = str(1)
        self.data["ids"] = "{}".format(user.id)
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_not_all_in_group_user(self):
        group = self.init_group()
        header = create_meeting_admin_user("user_admin")
        self.data["group_id"] = group.id
        user_ids = "-".join(User.objects.filter(id__lt=10).values_list("id", flat=True))
        self.data["ids"] = user_ids + "-100000"
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_permission(self):
        header = create_meetings_sponsor_user()
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_permission_2(self):
        header = create_user()
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)


class SponsorAddViewTest(TestCommon):
    url = "/sponsor/action/new/"
    data = {
        "ids": "1-2"
    }

    def test_ok(self):
        self.init_user(50)
        header = create_meeting_admin_user("user_admin")
        users = User.objects.all().values_list("id", flat=True)
        self.data["ids"] = "-".join(users)
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_200_OK)

    def test_over_count(self):
        self.init_user(60)
        header = create_meeting_admin_user("user_admin")
        users = User.objects.all().values_list("id", flat=True)
        self.data["ids"] = "-".join(users)
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lt_zero(self):
        self.init_user(1)
        header = create_meeting_admin_user("user_admin")
        self.data["ids"] = ""
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_not_all_in(self):
        self.init_user(50)
        header = create_meeting_admin_user("user_admin")
        users = User.objects.all().values_list("id", flat=True)
        User.objects.all().update(activity_level=2)
        self.data["ids"] = "-".join(users)
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_permission(self):
        header = create_meetings_sponsor_user()
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_permission_2(self):
        header = create_user()
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)


class SponsorDelViewTest(TestCommon):
    url = "sponsor/action/del/"
    data = {
        "ids": "1-2"
    }

    def test_ok(self):
        self.init_user(50)
        header = create_meeting_admin_user("user_admin")
        users = User.objects.all().values_list("id", flat=True)
        self.data["ids"] = "-".join(users)
        # todo 用戶注销后还可以删除吗？可以
        self.client.post(SponsorAddViewTest.url, hearder=header, data=SponsorAddViewTest.data)
        header = get_user("user_admin")
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_200_OK)

    def test_over_count(self):
        self.init_user(60)
        header = create_meeting_admin_user("user_admin")
        users = User.objects.all().values_list("id", flat=True)
        self.data["ids"] = "-".join(users)
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lt_zero(self):
        self.init_user(1)
        header = create_meeting_admin_user("user_admin")
        self.data["ids"] = ""
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_not_all_in(self):
        self.init_user(50)
        header = create_meeting_admin_user("user_admin")
        users = User.objects.all().values_list("id", flat=True)
        User.objects.all().update(activity_level=2)
        self.data["ids"] = "-".join(users)
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_permission(self):
        header = create_meetings_sponsor_user()
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_permission_2(self):
        header = create_user()
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)


class MeetingsViewTest(TestCommon):
    url = "/meetings/"
    data = {
        "topic": "*" * 128,  # string类型，会议名称，必填，长度限制128，限制内容中含有http，\r\n, xss攻击标签
        "platform": "zoom",  # string类型，平台，只能是以下参数: zoom,welink,tencent， 必填
        "sponsor": "T" * 20,  # string类型，会议发起人，必填，长度限制20，限制内容中含有http，\r\n, xss攻击标签

        "group_name": "*" * 40,  # string类型，sig 组名称，必填， 限制40
        "group_id": 1,  # int类型，sig组id, 必填
        "date": "2023-11-02",  # string类型，时间：2023-10-29，必填
        "start": "08:00",  # string类型，开始时间，必填
        "end": "09:00",  # string类型，结束时间，必填
        "etherpad": "https://etherpad.openeuler.org/p/A-Tune-meetingsdafssdfadsfasdfa",
        # string类型，以 https://etherpad.openeuler.org开头，必填，限制64
        "agenda": "*" * 4096,  # string类型，开会内容，必填，内容可以为空， 限制为4096，限制内容中含有http，\r\n, xss攻击标签
        "emaillist": ";".join(["{}@163.com".format("a" * 42) for _ in range(50)]),
        # string类型, 发送邮件，以;拼接，长度最长为1000，每封邮箱长度最长为50，限制20封，必填，内容可以为空
        "record": "cloud"  # string类型，是否自动录制，必填，可为空字符串，空字符串代表非自动录制，必填，内容可以为空
    }

    def test_ok(self):
        header, data = self.init_meetings(self.data)
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_200_OK)

    def test_topic(self):
        header, data = self.init_meetings(self.data)
        data["topic"] = "*" * 41
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_topic_1(self):
        header, data = self.init_meetings(self.data)
        data["topic"] = ""
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_platform(self):
        header, data = self.init_meetings(self.data)
        data["platform"] = "sadfdsfadsfadsfasd"
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_group_name(self):
        header, data = self.init_meetings(self.data)
        data["group_name"] = ""
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_group_id(self):
        header, data = self.init_meetings(self.data)
        data["group_id"] = "xxxxxx"
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_date(self):
        header, data = self.init_meetings(self.data)
        data["date"] = "xxxxxx"
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_date_1(self):
        header, data = self.init_meetings(self.data)
        data["date"] = "2025-11-02"
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_start(self):
        header, data = self.init_meetings(self.data)
        data["start"] = "08:13"
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_start_1(self):
        header, data = self.init_meetings(self.data)
        data["start"] = "xxx:13"
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_end(self):
        header, data = self.init_meetings(self.data)
        data["end"] = "08:13"
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_end_1(self):
        header, data = self.init_meetings(self.data)
        data["end"] = "xxx:13"
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_etherpad(self):
        header, data = self.init_meetings(self.data)
        data["etherpad"] = "*" * 65
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_agenda(self):
        header, data = self.init_meetings(self.data)
        data["agenda"] = "*" * 4097
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_agenda_2(self):
        header, data = self.init_meetings(self.data)
        data["agenda"] = xss_script
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_agenda_3(self):
        header, data = self.init_meetings(self.data)
        data["agenda"] = crlf_text
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_agenda_4(self):
        header, data = self.init_meetings(self.data)
        data["agenda"] = html_text
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_email_list(self):
        header, data = self.init_meetings(self.data)
        data["emaillist"] = ";".join(["{}@163.com".format("a" * 42) for _ in range(51)]),
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_email_list_1(self):
        header, data = self.init_meetings(self.data)
        data["emaillist"] = ";".join(["{}163.com".format("a" * 42) for _ in range(10)]),
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_email_list_2(self):
        header, data = self.init_meetings(self.data)
        data["emaillist"] = "sdajkfljlkdsjfk;asd@qq.com"
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_record(self):
        header, data = self.init_meetings(self.data)
        data["record"] = "cloudafdslfajsdlfjds"
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_permission(self):
        header = create_meeting_admin_user()
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_permission_2(self):
        header = create_user()
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_permission_3(self):
        header = create_activity_sponsor_user()
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_permission_4(self):
        header = create_activity_admin_user()
        ret = self.client.post(self.url, hearder=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)


class MeetingDelViewTest(TestCommon):
    url = "meeting/{}/"

    def test_ok(self):
        header, data = self.init_meetings(MeetingsViewTest.data)
        self.client.post(MeetingsViewTest.url, hearder=header, data=data)
        header = get_user("sponsor")
        m = Meeting.objects.first()
        url = self.url.format(m.mid)
        ret = self.client.delete(url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_200_OK)

    def test_not_delete_by_others(self):
        header, data = self.init_meetings(MeetingsViewTest.data)
        self.client.post(MeetingsViewTest.url, hearder=header, data=data)
        header = create_meetings_sponsor_user("xxxxxxx")
        m = Meeting.objects.first()
        url = self.url.format(m.mid)
        ret = self.client.delete(url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_permission_1(self):
        header = create_user()
        url = self.url.format(1)
        ret = self.client.delete(url, hearder=header)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_permission_2(self):
        header = create_activity_sponsor_user()
        url = self.url.format(1)
        ret = self.client.delete(url, hearder=header)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_permission_3(self):
        header = create_activity_admin_user()
        url = self.url.format(1)
        ret = self.client.delete(url, hearder=header)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)


class ActivityViewTest(TestCommon):
    url = "/activity/"
    data = {
        "title": "1" * 50,  # 活动主题，string类型，限制长度1-50
        "date": "2023-11-18",  # 日期，大于今天
        "activity_type": 1,  # 活动类型，1为线下活动，2为线上活动
        "register_url": "https://space.bilibili.com/527064077",  # 报名链接，url链接检查
        "synopsis": "*" * 4096,  # 活动简介，xss攻击检查，crlf攻击检查,限制长度4096
        "address": "*" * 100,  # 线下活动才有此字段
        "detail_address": "东城区灯市口利生大厦写字楼(锡拉胡同)",  # 线下活动才有此字段，详细地址, xss攻击检查，crlf攻击检查，限制长度100
        "longitude": "",  # 线下活动才有此字段，经度, xss攻击检查，crlf攻击检查，限制长度8位
        "latitude": "",  # 线下活动才有此字段，维度, xss攻击检查，crlf攻击检查，限制长度8位
        "start": "08:00",  # 线上活动才有此字段，开始时间
        "end": "09:00",  # 线上活动才有此字段，结束时间
        "poster": 1,  # 海报，目前只有1,2,3,4
        "schedules": [{  # 限制长度8192
            "start": "08:00",  # 开始时间, 时间限制08:00 -> 23:59
            "end": "09:00",  # 结束时间, 时间限制08:00 -> 23:59
            "topic": "活动1",  # 活动子主题, xss攻击检查，crlf攻击检查
            "speakerList": [{
                "name": "活动2",  # 嘉宾名称,xss攻击检查，crlf攻击检查
                "title": "工程师"  # 嘉宾职称,xss攻击检查，crlf攻击检查
            }]
        }],
    }

    def init_activity_data(self, is_online=True):
        temp = copy.deepcopy(self.data)
        if is_online:
            temp["activity_type"] = 2
            del temp["address"]
            del temp["detail_address"]
            del temp["longitude"]
            del temp["latitude"]
        else:
            temp["activity_type"] = 1
            del temp["start"]
            del temp["end"]
        return temp

    def test_ok(self):
        data = self.init_activity_data()
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_200_OK)

    def test_invalid_title(self):
        data = self.init_activity_data()
        del data["title"]
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_title_1(self):
        data = self.init_activity_data()
        data["title"] = "a" * 51
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_title_2(self):
        data = self.init_activity_data()
        data["title"] = html_text
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_title_3(self):
        data = self.init_activity_data()
        data["title"] = xss_script
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_date(self):
        data = self.init_activity_data()
        data["date"] = "2306-11-19"
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")

        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_date_1(self):
        data = self.init_activity_data()
        data["date"] = "dsfafdsfadsfasd"
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_activity_type(self):
        data = self.init_activity_data()
        data["activity_type"] = 3
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_register_url(self):
        data = self.init_activity_data()
        data["register_url"] = "dsfadsfasdfasdfadsfa"
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_synopsis(self):
        data = self.init_activity_data()
        data["synopsis"] = "*" * 4097
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_address(self):
        data = self.init_activity_data(is_online=False)
        data["address"] = "*" * 101
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_detail_address(self):
        data = self.init_activity_data(is_online=False)
        data["detail_address"] = "*" * 101
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_longitude(self):
        data = self.init_activity_data(is_online=False)
        data["longitude"] = "*" * 101
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_longitude_1(self):
        data = self.init_activity_data(is_online=False)
        data["longitude"] = "312312312.312312312312"
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_latitude(self):
        data = self.init_activity_data(is_online=False)
        data["latitude"] = "*" * 101
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_start(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["latitude"] = "*" * 101
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_start_1(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["start"] = "08:13"
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_start_2(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["start"] = "xxx:13"
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_end_1(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["end"] = "08:13"
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_end_2(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["end"] = "xxx:13"
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_poster(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["poster"] = "5"
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_schedules(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["schedules"] = "*" * 8193
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_schedules_1(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["schedules"] = [{  # 限制长度8192
            "start": "08:00",  # 开始时间, 时间限制08:00 -> 23:59
            "end": "09:00",  # 结束时间, 时间限制08:00 -> 23:59
            "topic": "活动1",  # 活动子主题, xss攻击检查，crlf攻击检查
            "speakerList": [{
                "name": xss_script,  # 嘉宾名称,xss攻击检查，crlf攻击检查
                "title": "工程师"  # 嘉宾职称,xss攻击检查，crlf攻击检查
            }]
        }],
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_schedules_2(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["schedules"] = [{  # 限制长度8192
            "start": "08:00",  # 开始时间, 时间限制08:00 -> 23:59
            "end": "09:00",  # 结束时间, 时间限制08:00 -> 23:59
            "topic": "活动1",  # 活动子主题, xss攻击检查，crlf攻击检查
            "speakerList": [{
                "name": html_text,  # 嘉宾名称,xss攻击检查，crlf攻击检查
                "title": "工程师"  # 嘉宾职称,xss攻击检查，crlf攻击检查
            }]
        }],
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_schedules_3(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["schedules"] = [{  # 限制长度8192
            "start": "08:00",  # 开始时间, 时间限制08:00 -> 23:59
            "end": "09:00",  # 结束时间, 时间限制08:00 -> 23:59
            "topic": "活动1",  # 活动子主题, xss攻击检查，crlf攻击检查
            "speakerList": [{
                "name": crlf_text,  # 嘉宾名称,xss攻击检查，crlf攻击检查
                "title": "工程师"  # 嘉宾职称,xss攻击检查，crlf攻击检查
            }]
        }],
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_schedules_4(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["schedules"] = [{  # 限制长度8192
            "start": "08:00",  # 开始时间, 时间限制08:00 -> 23:59
            "end": "09:00",  # 结束时间, 时间限制08:00 -> 23:59
            "topic": "活动1",  # 活动子主题, xss攻击检查，crlf攻击检查
            "speakerList": [{
                "name": "name",  # 嘉宾名称,xss攻击检查，crlf攻击检查
                "title": xss_script  # 嘉宾职称,xss攻击检查，crlf攻击检查
            }]
        }],
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_schedules_5(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["schedules"] = [{  # 限制长度8192
            "start": "08:00",  # 开始时间, 时间限制08:00 -> 23:59
            "end": "09:00",  # 结束时间, 时间限制08:00 -> 23:59
            "topic": "活动1",  # 活动子主题, xss攻击检查，crlf攻击检查
            "speakerList": [{
                "name": "name",  # 嘉宾名称,xss攻击检查，crlf攻击检查
                "title": html_text  # 嘉宾职称,xss攻击检查，crlf攻击检查
            }]
        }],
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_schedules_6(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["schedules"] = [{  # 限制长度8192
            "start": "08:00",  # 开始时间, 时间限制08:00 -> 23:59
            "end": "09:00",  # 结束时间, 时间限制08:00 -> 23:59
            "topic": "活动1",  # 活动子主题, xss攻击检查，crlf攻击检查
            "speakerList": [{
                "name": "name",  # 嘉宾名称,xss攻击检查，crlf攻击检查
                "title": crlf_text  # 嘉宾职称,xss攻击检查，crlf攻击检查
            }]
        }],
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_schedules_7(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["schedules"] = [{  # 限制长度8192
            "start": "08:00",  # 开始时间, 时间限制08:00 -> 23:59
            "end": "09:00",  # 结束时间, 时间限制08:00 -> 23:59
            "topic": crlf_text,  # 活动子主题, xss攻击检查，crlf攻击检查
            "speakerList": [{
                "name": "name",  # 嘉宾名称,xss攻击检查，crlf攻击检查
                "title": "title"  # 嘉宾职称,xss攻击检查，crlf攻击检查
            }]
        }],
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_schedules_8(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["schedules"] = [{  # 限制长度8192
            "start": "08:00",  # 开始时间, 时间限制08:00 -> 23:59
            "end": "09:00",  # 结束时间, 时间限制08:00 -> 23:59
            "topic": html_text,  # 活动子主题, xss攻击检查，crlf攻击检查
            "speakerList": [{
                "name": "name",  # 嘉宾名称,xss攻击检查，crlf攻击检查
                "title": "title"  # 嘉宾职称,xss攻击检查，crlf攻击检查
            }]
        }],
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_schedules_9(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["schedules"] = [{  # 限制长度8192
            "start": "08:00",  # 开始时间, 时间限制08:00 -> 23:59
            "end": "09:00",  # 结束时间, 时间限制08:00 -> 23:59
            "topic": xss_script,  # 活动子主题, xss攻击检查，crlf攻击检查
            "speakerList": [{
                "name": "name",  # 嘉宾名称,xss攻击检查，crlf攻击检查
                "title": "title"  # 嘉宾职称,xss攻击检查，crlf攻击检查
            }]
        }],
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_schedules_10(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["schedules"] = [{  # 限制长度8192
            "start": "08:01",  # 开始时间, 时间限制08:00 -> 23:59
            "end": "09:00",  # 结束时间, 时间限制08:00 -> 23:59
            "topic": "topic",  # 活动子主题, xss攻击检查，crlf攻击检查
            "speakerList": [{
                "name": "name",  # 嘉宾名称,xss攻击检查，crlf攻击检查
                "title": "title"  # 嘉宾职称,xss攻击检查，crlf攻击检查
            }]
        }],
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_schedules_11(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["schedules"] = [{  # 限制长度8192
            "start": "07:00",  # 开始时间, 时间限制08:00 -> 23:59
            "end": "09:00",  # 结束时间, 时间限制08:00 -> 23:59
            "topic": "topic",  # 活动子主题, xss攻击检查，crlf攻击检查
            "speakerList": [{
                "name": "name",  # 嘉宾名称,xss攻击检查，crlf攻击检查
                "title": "title"  # 嘉宾职称,xss攻击检查，crlf攻击检查
            }]
        }],
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_schedules_12(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["schedules"] = [{  # 限制长度8192
            "start": "07:00",  # 开始时间, 时间限制08:00 -> 23:59
            "end": "23:00",  # 结束时间, 时间限制08:00 -> 23:59
            "topic": "topic",  # 活动子主题, xss攻击检查，crlf攻击检查
            "speakerList": [{
                "name": "name",  # 嘉宾名称,xss攻击检查，crlf攻击检查
                "title": "title"  # 嘉宾职称,xss攻击检查，crlf攻击检查
            }]
        }],
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_schedules_13(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        data["schedules"] = [{  # 限制长度8192
            "start": "07:00",  # 开始时间, 时间限制08:00 -> 23:59
            "end": "20:60",  # 结束时间, 时间限制08:00 -> 23:59
            "topic": "topic",  # 活动子主题, xss攻击检查，crlf攻击检查
            "speakerList": [{
                "name": "name",  # 嘉宾名称,xss攻击检查，crlf攻击检查
                "title": "title"  # 嘉宾职称,xss攻击检查，crlf攻击检查
            }]
        }],
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_permission(self):
        data = self.init_activity_data(is_online=False)
        header = create_activity_admin_user()
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_permission_1(self):
        data = self.init_activity_data(is_online=False)
        header = create_user()
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_permission_2(self):
        data = self.init_activity_data(is_online=False)
        header = create_meeting_admin_user()
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_permission_3(self):
        data = self.init_activity_data(is_online=False)
        header = create_meetings_sponsor_user()
        ret = self.client.post(self.url, hearder=header, data=data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)


class ActivityPublishViewTest(TestCommon):
    url = "activitypublish/{}/"

    def test_ok(self):
        data = ActivityViewTest().init_activity_data()
        header = create_activity_admin_user("sponsor", "sponsor_openid")
        self.client.post(ActivityViewTest.url, hearder=header, data=data)
        header = get_user("sponsor")
        activity = Activity.objects.first()
        url = self.url.format(activity.id)
        ret = self.client.put(url, header=header)
        self.assertEqual(ret.status_code, status.HTTP_200_OK)

    def test_not_exist(self):
        header = create_activity_admin_user("sponsor", "sponsor_openid")
        url = self.url.format("20000")
        ret = self.client.put(url, header=header)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_not_permission(self):
        header = create_user("sponsor", "sponsor_openid")
        url = self.url.format("20000")
        ret = self.client.put(url, header=header)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_permission_1(self):
        header = create_meetings_sponsor_user("sponsor", "sponsor_openid")
        url = self.url.format("20000")
        ret = self.client.put(url, header=header)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_permission_2(self):
        header = create_meeting_admin_user("sponsor", "sponsor_openid")
        url = self.url.format("20000")
        ret = self.client.put(url, header=header)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_permission_3(self):
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        url = self.url.format("20000")
        ret = self.client.put(url, header=header)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)


class ActivityRejectViewTest(TestCommon):
    url = "activityreject/{}/"

    def test_ok(self):
        data = ActivityViewTest().init_activity_data()
        header = create_activity_admin_user("sponsor", "sponsor_openid")
        self.client.post(ActivityViewTest.url, hearder=header, data=data)
        header = get_user("sponsor")
        activity = Activity.objects.first()
        url = self.url.format(activity.id)
        ret = self.client.put(url, header=header)
        self.assertEqual(ret.status_code, status.HTTP_200_OK)

    def test_not_exist(self):
        header = create_activity_admin_user("sponsor", "sponsor_openid")
        url = self.url.format("20000")
        ret = self.client.put(url, header=header)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_not_permission(self):
        header = create_user("sponsor", "sponsor_openid")
        url = self.url.format("20000")
        ret = self.client.put(url, header=header)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_permission_1(self):
        header = create_meetings_sponsor_user("sponsor", "sponsor_openid")
        url = self.url.format("20000")
        ret = self.client.put(url, header=header)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_permission_2(self):
        header = create_meeting_admin_user("sponsor", "sponsor_openid")
        url = self.url.format("20000")
        ret = self.client.put(url, header=header)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_permission_3(self):
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        url = self.url.format("20000")
        ret = self.client.put(url, header=header)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)


class ActivityDelViewTest(TestCommon):
    url = "/activitydel/{}/"

    def test_ok(self):
        data = ActivityViewTest().init_activity_data()
        header = create_activity_admin_user("sponsor", "sponsor_openid")
        self.client.post(ActivityViewTest.url, hearder=header, data=data)
        header = get_user("sponsor")
        activity = Activity.objects.first()
        url = ActivityPublishViewTest.url.format(activity.id)
        self.client.put(url, header=header)
        header = get_user("sponsor")
        url = self.url.format(activity.id)
        ret = self.client.put(url, header=header)
        self.assertEqual(ret.status_code, status.HTTP_200_OK)

    def test_not_permission(self):
        header = create_user("sponsor", "sponsor_openid")
        url = self.url.format("20000")
        ret = self.client.put(url, header=header)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_permission_1(self):
        header = create_meetings_sponsor_user("sponsor", "sponsor_openid")
        url = self.url.format("20000")
        ret = self.client.put(url, header=header)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_permission_2(self):
        header = create_meeting_admin_user("sponsor", "sponsor_openid")
        url = self.url.format("20000")
        ret = self.client.put(url, header=header)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_permission_3(self):
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        url = self.url.format("20000")
        ret = self.client.put(url, header=header)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)


class ActivityUpdateViewTest(TestCommon):
    url = "/activityupdate/{}/"
    data = {
        "schedules": json.dumps(
            [{
                "start": "08:00",  # 开始时间, 时间限制08:00 -> 23:59
                "end": "09:00",  # 结束时间, 时间限制08:00 -> 23:59
                "topic": "xxjflasdfads",  # 活动子主题, xss攻击检查，crlf攻击检查
                "speakerList": [{
                    "name": "name",  # 嘉宾名称,xss攻击检查，crlf攻击检查
                    "title": "title"  # 嘉宾职称,xss攻击检查，crlf攻击检查
                }]
            }]
        )
    }

    def test_ok(self):
        data = ActivityViewTest().init_activity_data()
        header = create_activity_admin_user("sponsor", "sponsor_openid")
        self.client.post(ActivityViewTest.url, hearder=header, data=data)
        header = get_user("sponsor")
        activity = Activity.objects.first()
        url = ActivityPublishViewTest.url.format(activity.id)
        self.client.put(url, header=header)
        header = get_user("sponsor")
        url = self.url.format(activity.id)
        ret = self.client.put(url, header=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_200_OK)

    def test_not_exist(self):
        data = ActivityViewTest().init_activity_data()
        header = create_activity_admin_user("sponsor", "sponsor_openid")
        self.client.post(ActivityViewTest.url, hearder=header, data=data)
        header = get_user("sponsor")
        activity = Activity.objects.first()
        url = ActivityPublishViewTest.url.format(activity.id)
        self.client.put(url, header=header)
        header = get_user("sponsor")
        url = self.url.format("11111")
        ret = self.client.put(url, header=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_400_BAD_REQUEST)

    def test_not_permission(self):
        header = create_user("sponsor", "sponsor_openid")
        url = self.url.format("20000")
        ret = self.client.put(url, header=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_permission_1(self):
        header = create_meetings_sponsor_user("sponsor", "sponsor_openid")
        url = self.url.format("20000")
        ret = self.client.put(url, header=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_permission_2(self):
        header = create_meeting_admin_user("sponsor", "sponsor_openid")
        url = self.url.format("20000")
        ret = self.client.put(url, header=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_permission_3(self):
        header = create_activity_sponsor_user("sponsor", "sponsor_openid")
        url = self.url.format("20000")
        ret = self.client.put(url, header=header, data=self.data)
        self.assertEqual(ret.status_code, status.HTTP_403_FORBIDDEN)
