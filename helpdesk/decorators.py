from django.contrib.auth.models import Group

def has_group(user, group_names):
    """Verifica si un usuario pertenece a alguno de los grupos dados."""
    if user.is_superuser:
        return True
    if not isinstance(group_names, list):
        group_names = [group_names]
    return user.groups.filter(name__in=group_names).exists()
