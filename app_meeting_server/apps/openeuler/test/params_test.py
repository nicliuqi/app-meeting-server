#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/11/8 21:37
# @Author  : TomNewChao
# @File    : params_test.py
# @Description :
from unittest import mock
from rest_framework.test import APITestCase


class LoginTest(APITestCase):
    def setUp(self) -> None:
        self.value = "*" * 16
        self.url = "/login"
        self.data = {
            "code": self.value
        }

    @mock.patch("app_meeting_server.utils.wx_api.get_openid")
    def test_login_ok(self, mock_get_openid):
        mock_get_openid.return_value = {
            "openid": self.value
        }
        ret = self.client.post(self.url, data=self.data)
        self.assertEqual(ret.status_code, 200)

    def test_login_lack_openid(self):
        ret = self.client.post(self.url, data=dict())
        self.assertEqual(ret.status_code, 400)
