from rest_framework import status
from rest_framework.test import APITestCase

from openeuler.test.common import create_user


class LoginViewTest(APITestCase):
    def setUp(self) -> None:
        self.value = "*" * 16
        self.url = "/login/"

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
    def setUp(self) -> None:
        self.url = "/refresh/"

    def test_refresh_lack_refresh(self):
        ret = self.client.post(self.url, data={})
        self.assertEqual(ret.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_not_match(self):
        ret = self.client.post(self.url, data={"refresh": "match"})
        self.assertEqual(ret.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_ok(self):
        create_user("test_refresh_ok", "test_refresh_ok")

