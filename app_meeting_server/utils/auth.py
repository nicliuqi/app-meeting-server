import logging
from django.utils.translation import ugettext_lazy as _
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.settings import api_settings
from app_meeting_server.utils.common import make_signature
from django.conf import settings
from django.contrib.auth import get_user_model
from app_meeting_server.utils.ret_api import MyValidationError
from app_meeting_server.utils.ret_code import RetCode

logger = logging.getLogger('log')


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
            logger.error("Token contained no recognizable user identification")
            raise InvalidToken(_('Token contained no recognizable user identification'))

        user_model = get_user_model()
        try:
            user = user_model.objects.get(**{api_settings.USER_ID_FIELD: user_id})
        except user_model.DoesNotExist:
            logger.error("User:{} not found".format(str(user_id)))
            raise AuthenticationFailed(_('User not found'), code='user_not_found')

        if not user.is_delete == 0:
            logger.error("User:{} is inactive".format(str(user_id)))
            raise AuthenticationFailed(_('User is inactive'), code='user_inactive')

        if user.nickname == settings.ANONYMOUS_NAME:
            logger.error("User:{} is anonymous".format(str(user_id)))
            raise AuthenticationFailed(_('User is anonymous'), code='user_anonymous')

        token = make_signature(validated_token)
        if user.signature != str(token):
            logger.error("User:{} token has expired".format(str(user_id)))
            raise InvalidToken(_('Token has expired'))
        if user.agree_privacy_policy != 1:
            logger.error("User:{} has no agreement about privacy policy".format(str(user_id)))
            raise MyValidationError(RetCode.STATUS_DISAGREE_PRIVACY)
        if user.agree_privacy_policy_version != settings.PRIVACY_POLICY_VERSION:
            logger.error("User:{} has does not agree the latest privacy policy".format(str(user_id)))
            raise MyValidationError(RetCode.STATUS_OLD_PRIVACY)
        return user


class CustomAuthenticationWithoutPolicyAgreen(JWTAuthentication):
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
            logger.error("Token contained no recognizable user identification")
            raise InvalidToken(_('Token contained no recognizable user identification'))

        user_model = get_user_model()
        try:
            user = user_model.objects.get(**{api_settings.USER_ID_FIELD: user_id})
        except user_model.DoesNotExist:
            logger.error("User:{} not found".format(str(user_id)))
            raise AuthenticationFailed(_('User not found'), code='user_not_found')

        if not user.is_delete == 0:
            logger.error("User:{} is inactive".format(str(user_id)))
            raise AuthenticationFailed(_('User is inactive'), code='user_inactive')

        if user.nickname == settings.ANONYMOUS_NAME:
            logger.error("User:{} is anonymous".format(str(user_id)))
            raise AuthenticationFailed(_('User is anonymous'), code='user_anonymous')

        token = make_signature(validated_token)
        if user.signature != str(token):
            logger.error("User:{} token has expired".format(str(user_id)))
            raise InvalidToken(_('Token has expired'))
        return user
