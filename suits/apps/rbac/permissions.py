from rest_framework.permissions import BasePermission
from .services import user_has_permission

class HasPlatformPermission(BasePermission):
    """
    Check if the user has a specific permission.
    The permission should be defined on the view as `required_permission`.
    """

    def has_permission(self, request, view):
        # Get the required_permission from the view
        required_permission = getattr(view, "required_permission", None)

        # If no permission is required, allow access
        if not required_permission:
            return True

        # Call your service to check the user's permission
        return user_has_permission(request.user, required_permission)