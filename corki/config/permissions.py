from rest_framework.permissions import BasePermission

class IsAuthenticatedOrGuest(BasePermission):
    def has_permission(self, request, view):
        # 允许匿名用户访问特定的接口
        if hasattr(view, 'allow_guest') and view.allow_guest:
            return True
        else:
            if request.user.id == 0:
                return False
        return False
