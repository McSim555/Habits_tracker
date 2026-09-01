from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):

    def has_permission(self, request, view):
        # Анонимным пользователям доступ запрещен
        if not request.user or not request.user.is_authenticated:
            return False

        if view.action == 'create':
            return request.user.is_authenticated

        return True

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS and obj.is_public:
            return True

        return obj.owner == request.user