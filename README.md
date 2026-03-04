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

## Migraciones e Inicialización

1. Aplicar las migraciones a la base de datos:
   ```bash
   python manage.py migrate
   ```

2. Crear los grupos y permisos básicos (Comando personalizado):
   ```bash
   python manage.py setup_roles
   ```

3. Crear un superusuario temporal (para acceso ADMIN total al admin de Django y al sistema):
   ```bash
   python manage.py createsuperuser
   ```
   *Nota: Asignarle el grupo ADMIN o usarlo directamente como superusuario.*

## Ejecución

1. Iniciar el servidor de desarrollo:
   ```bash
   python manage.py runserver
   ```

2. Acceder al sistema en `http://127.0.0.1:8000/`.

## Subida de Archivos Adjuntos

El sistema utiliza la carpeta `media/` en la raíz del proyecto para almacenar los archivos adjuntos. Durante el desarrollo, Django sirve estos archivos gracias a la configuración en `urls.py`. Asegúrate de tener permisos de escritura en la carpeta donde ejecutas el proyecto.
