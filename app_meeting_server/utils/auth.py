from django.utils.translation import ugettext_lazy as _
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.state import User
from app_meeting_server.utils.common import make_signature
from django.conf import settings


class CustomAuthentication(JWTAuthentication):
    """
    CustomAuthentication override get_user
    """

    def get_user(self, validated_token):
        """
        Attempts to find and return a user using the given validated token.
        """
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken(_('Token contained no recognizable user identification'))

        try:
            user = User.objects.get(**{api_settings.USER_ID_FIELD: user_id})
        except User.DoesNotExist:
            raise AuthenticationFailed(_('User not found'), code='user_not_found')

        if not user.is_delete == 0:
            raise AuthenticationFailed(_('User is inactive'), code='user_inactive')

        if user.nickname == settings.ANONYMOUS_NAME:
            raise AuthenticationFailed(_('User is anonymous'), code='user_anonymous')

        token = make_signature(validated_token)
        if user.signature != str(token):
            raise InvalidToken(_('Token has expired'))

        return user
