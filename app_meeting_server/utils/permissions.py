import logging
from django.conf import settings
from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger('log')


class MaintainerPermission(permissions.IsAuthenticated):
    """Maintainer权限"""
    message = '需要Maintainer权限！！！'
    level = 2

    def has_permission(self, request, view):  # 对于列表的访问权限
        if request.user.is_anonymous:
            logger.error("user:{} is anonymous".format(str(request.user.id)))
            return False
        if not request.user.level:
            logger.error("user:{} has no permission".format(str(request.user.id)))
            return False
        if request.user.level == self.level:
            if User.objects.get(id=request.user.id, level=request.user.level):
                return True
            else:
                logger.error("user:{} has no permission".format(str(request.user.id)))
                return False
        else:
            logger.error("user:{} has no permission".format(str(request.user.id)))
            return False

    def has_object_permission(self, request, view, obj):  # 对于对象的访问权限
        return self.has_permission(request, view)


class SponsorPermission(permissions.IsAuthenticated):
    """活动发起人权限"""
    message = '需要活动发起人权限'
    activity_level = 2

    def has_permission(self, request, view):  # 对于列表的访问权限
        if request.user.is_anonymous:
            logger.error("user:{} is anonymous".format(str(request.user.id)))
            return False
        if not request.user.activity_level:
            logger.error("user:{} has no permission".format(str(request.user.id)))
            return False
        if request.user.activity_level == self.activity_level:
            if User.objects.get(id=request.user.id, activity_level=request.user.activity_level):
                return True
            else:
                logger.error("user:{} has no permission".format(str(request.user.id)))
                return False
        else:
            logger.error("user:{} has no permission".format(str(request.user.id)))
            return False

    def has_object_permission(self, request, view, obj):  # 对于对象的访问权限
        return self.has_permission(request, view)


class MeetigsAdminPermission(MaintainerPermission):
    """会议管理员权限"""
    message = '需要会议管理员权限！！！'
    level = 3


class ActivityAdminPermission(SponsorPermission):
    """活动管理员权限"""
    message = '需要活动管理员权限！！！'
    activity_level = 3


class MaintainerAndAdminPermission(permissions.IsAuthenticated):
    message = '需要Maintainer或者会议管理员权限！！！'
    level = 2

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            logger.error("user:{} is anonymous".format(str(request.user.id)))
            return False
        if not request.user.level:
            logger.error("user:{} has no permission".format(str(request.user.id)))
            return False
        if request.user.level >= self.level:
            if User.objects.get(id=request.user.id, level=request.user.level):
                return True
            else:
                logger.error("user:{} has no permission".format(str(request.user.id)))
                return False
        else:
            logger.error("user:{} has no permission".format(str(request.user.id)))
            return False

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class AdminPermission(permissions.IsAuthenticated):
    """需要会议管理员权限或者活动管理者权限！！！"""
    message = "需要会议管理员权限或者活动管理者权限！！！"
    level = 3
    activity_level = 3

    def has_permission(self, request, view):  # 对于列表的访问权限
        if request.user.is_anonymous:
            logger.error("user:{} is anonymous".format(str(request.user.id)))
            return False
        elif request.user.level == self.level:
            if User.objects.get(id=request.user.id, level=request.user.level):
                return True
            else:
                logger.error("user:{} has no permission".format(str(request.user.id)))
                return False
        elif request.user.activity_level == self.activity_level:
            if User.objects.get(id=request.user.id, activity_level=request.user.activity_level):
                return True
            else:
                logger.error("user:{} has no permission".format(str(request.user.id)))
                return False
        else:
            logger.error("user:{} has no permission".format(str(request.user.id)))
            return False

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class QueryPermission(permissions.BasePermission):
    """查询权限"""

    def has_permission(self, request, view):
        token = request.GET.get('token')
        if token and token == settings.QUERY_TOKEN:
            return True
        else:
            logger.error("QueryPermission has no permission")
            return False


class ActivitiesQueryPermission(permissions.BasePermission):
    """活动查询权限"""

    def has_permission(self, request, view):
        token = request.GET.get('token')
        activity = request.GET.get('activity')
        activity_type = request.GET.get('activity_type')
        if not activity_type and activity and activity in ['registering', 'going', 'completed']:
            return True
        if not activity and activity_type and activity_type in ['1', '2']:
            return True
        if activity and activity_type:
            if activity in ['registering', 'going', 'completed'] and activity_type in ['1', '2']:
                return True
            else:
                logger.error("ActivitiesQueryPermission has no permission")
                return False
        if not activity and not activity_type:
            if token and token == settings.QUERY_TOKEN:
                return True
            else:
                logger.error("ActivitiesQueryPermission has no permission")
                return False
