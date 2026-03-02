def user_has_permission(user, code):
    roles = user.userrole_set.select_related("role").all()
    for user_role in roles:
        if user_role.role.permissions.filter(code=code).exists():
            return True
    return False