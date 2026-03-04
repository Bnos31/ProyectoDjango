from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group

class Command(BaseCommand):
    help = 'Crea usuarios de prueba para cada rol del sistema.'

    def handle(self, *args, **kwargs):
        usuarios = [
            {'username': 'admin_user',      'password': 'Admin1234!',    'email': 'admin@helpdesk.com',      'group': 'ADMIN',      'is_staff': True},
            {'username': 'supervisor_user', 'password': 'Super1234!',    'email': 'sup@helpdesk.com',        'group': 'SUPERVISOR', 'is_staff': False},
            {'username': 'tecnico_user',    'password': 'Tecnico1234!',  'email': 'tec@helpdesk.com',        'group': 'TECNICO',    'is_staff': False},
        ]

        for u in usuarios:
            if User.objects.filter(username=u['username']).exists():
                self.stdout.write(self.style.WARNING(f'Usuario "{u["username"]}" ya existe, omitiendo.'))
                continue

            user = User.objects.create_user(
                username=u['username'],
                password=u['password'],
                email=u['email'],
                is_staff=u['is_staff'],
            )

            try:
                group = Group.objects.get(name=u['group'])
                user.groups.add(group)
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Usuario "{u["username"]}" creado con contraseña "{u["password"]}" → grupo {u["group"]}'
                ))
            except Group.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f'El grupo {u["group"]} no existe. Ejecuta setup_roles primero.'
                ))
