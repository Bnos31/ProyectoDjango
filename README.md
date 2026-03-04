# Help Desk Universitario

Este es un sistema de Help Desk de mantenimiento desarrollado en Django 5 y PostgreSQL.

## Requisitos Previos
- Python 3.11+
- PostgreSQL

## Configuración del Entorno Virtual

1. Crear el entorno virtual:
   ```bash
   python -m venv venv
   ```

2. Activar el entorno virtual:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

## Configuración de Base de Datos

1. Crear una base de datos en PostgreSQL llamada `helpdesk_db`.
2. El usuario por defecto configurado en `settings.py` es `postgres` con contraseña `postgres` en `localhost:5432`.
   - Puedes cambiar estos valores en `helpdesk_project/settings.py` si es necesario.

## Pasos de Configuración Inicial (solo una vez)

1. Levantar la base de datos con Docker:
   ```bash
   docker-compose up -d
   ```

2. Crear y aplicar las migraciones a la base de datos:
   ```bash
   python manage.py makemigrations helpdesk
   python manage.py migrate
   ```

3. Crear los grupos y permisos básicos:
   ```bash
   python manage.py setup_roles
   ```

4. Crear un superusuario (acceso total al sistema):
   ```bash
   python manage.py createsuperuser
   ```
   *En el panel `/admin/`, asigna el grupo ADMIN/SUPERVISOR/TECNICO a los usuarios que necesites.*

## Ejecución Diaria

Cada vez que quieras trabajar, simplemente ejecuta:

```bash
docker-compose up -d       # Levanta la base de datos (si no está corriendo)
python manage.py runserver # Levanta el servidor Django
```

Accede al sistema en `http://127.0.0.1:8000/` y al panel de administración en `http://127.0.0.1:8000/admin/`.

## Subida de Archivos Adjuntos

El sistema utiliza la carpeta `media/` en la raíz del proyecto para almacenar los archivos adjuntos. Durante el desarrollo, Django sirve estos archivos gracias a la configuración en `urls.py`. Asegúrate de tener permisos de escritura en la carpeta donde ejecutas el proyecto.
