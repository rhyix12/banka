from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminOrProvincialOrMunicipal(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_role in ['admin', 'provincial_agriculturist', 'municipal_agriculturist']
        )

class IsAdminOrProvincialOrAgriculturistReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            if request.user.user_role == 'admin':
                return True
            if request.user.user_role == 'provincial' and request.method in SAFE_METHODS:
                return True
            if request.user.user_role == 'agriculturist' and request.method in SAFE_METHODS:
                return True
        return False

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_role == 'admin'

class IsStaffOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.user_role in ['admin', 'provincial_agriculturist', 'municipal_agriculturist'])

class IsSelfOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.user_role == 'admin' or obj == request.user