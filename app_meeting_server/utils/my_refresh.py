# -*- coding: utf-8 -*-
# @Time    : 2023/12/4 18:18
# @Author  : Tom_zc
# @FileName: my_refresh.py
# @Software: PyCharm
import secrets

from rest_framework_simplejwt.serializers import TokenObtainSerializer
from rest_framework_simplejwt.tokens import Token
from rest_framework_simplejwt.settings import api_settings


class MyToken(Token):
    def set_jti(self):
        self.payload[api_settings.JTI_CLAIM] = secrets.token_hex(24)


class MyAccessToken(MyToken):
    token_type = 'access'
    lifetime = api_settings.ACCESS_TOKEN_LIFETIME


class MyRefreshToken(MyToken):
    token_type = 'refresh'
    lifetime = api_settings.REFRESH_TOKEN_LIFETIME
    no_copy_claims = (
        api_settings.TOKEN_TYPE_CLAIM,
        'exp',

        # Both of these claims are included even though they may be the same.
        # It seems possible that a third party token might have a custom or
        # namespaced JTI claim as well as a default "jti" claim.  In that case,
        # we wouldn't want to copy either one.
        api_settings.JTI_CLAIM,
        'jti',
    )

    @property
    def access_token(self):
        """
        Returns an access token created from this refresh token.  Copies all
        claims present in this refresh token to the new access token except
        those claims listed in the `no_copy_claims` attribute.
        """
        access = MyAccessToken()

        # Use instantiation time of refresh token as relative timestamp for
        # access token "exp" claim.  This ensures that both a refresh and
        # access token expire relative to the same time if they are created as
        # a pair.
        access.set_exp(from_time=self.current_time)

        no_copy = self.no_copy_claims
        for claim, value in self.payload.items():
            if claim in no_copy:
                continue
            access[claim] = value

        return access


class MyTokenObtainPairSerializer(TokenObtainSerializer):
    @classmethod
    def get_token(cls, user):
        return MyRefreshToken.for_user(user)

    def validate(self, attrs):
        data = super().validate(attrs)

        refresh = self.get_token(self.user)

        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)

        return data
