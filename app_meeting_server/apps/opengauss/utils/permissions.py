from rest_framework import permissions
from opengauss.models import GroupUser


class MaintainerPermission(permissions.IsAuthenticated):
    """Maintainer权限"""
    message = '需要Maintainer权限！！！'

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False
        if GroupUser.objects.filter(user_id=request.user.id):
            return True

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)