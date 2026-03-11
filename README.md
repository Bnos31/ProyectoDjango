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

## Módulo de Inteligencia Artificial (RAG)

El sistema integra un bot de Inteligencia Artificial que lee documentos (PDF/DOCX/TXT) y responde preguntas basadas en ellos usando Langchain y ChromaDB.

### Arquitectura Docker Completa (RAG 100% Local / Offline)

El sistema ahora soporta `docker-compose` íntegro con la siguiente arquitectura:
- Django (Puerto 8000)
- PostgreSQL (Puerto 5433 en host / 5432 interno)
- Ollama LLM (Puerto 11434)
- ChromaDB persisente como volumen Docker en `/vectorstore`

### Pasos para probar el chat RAG Offline

1. Construye e inicia la infraestructura completa en Docker:
   ```bash
   docker-compose up -d --build
   ```
2. Ejecuta las migraciones y la carga de datos inicial si es la primera vez (en el contenedor):
   ```bash
   docker exec -it helpdesk_django python manage.py makemigrations helpdesk
   docker exec -it helpdesk_django python manage.py migrate
   docker exec -it helpdesk_django python manage.py setup_roles
   docker exec -it helpdesk_django python manage.py create_test_users
   # O crea un super_usuario si lo requieres
   ```
3. **Paso crítico**: Ollama empieza sin modelos por defecto. Necesitas descargar internamente Llama 3:
   ```bash
   docker exec -it helpdesk_ollama ollama run llama3
   ```
   *Esto descargará ~4.7GB la primera vez, deja que termine.*

4. Ingresa a la app en http://localhost:8000 e inicia sesión.
5. Ve a **Doc. IA** (`/rag/cargar-documentos`) sube tus archivos (PDF, DOCX o TXT). El sistema usará Embeddings locales (HuggingFace sentence-transformers) de forma gratuita y offline.
6. Ve a **Chat IA** (`/rag/chat`) y haz una pregunta, Django contactará con el contenedor de Ollama HTTP (`http://ollama:11434`) y utilizará el modelo llama3 para responderte basándose en tus documentos.

## Módulo Analítico Predictivo (Machine Learning)

El sistema ahora cuenta con un algoritmo avanzado de `RandomForestClassifier` construido usando la biblioteca `scikit-learn`. Este módulo detecta los patrones de degradación basados en el flujo histórico de tickets (Incidencias pasadas) permitiendo arrojar una "Probabilidad de Fallo Crítico".

### Entrenar el Modelo (Requerido)

El modelo **necesita** de datos reales en el sistema para poder aprender y generar el archivo binario pre-entrenado `.pkl`. Necesitas haber generado **al menos 5 incidencias diferentes** (con mezcla de prioridades ALTA/CRÍTICAMENTE afectadas y BAJAS) para que surta efecto. ¡Toda Incidencia nueva que ocurra sirve de conocimiento!.

Desde la terminal local o dentro del contenedor, ejecuta los siguientes pasos (*Si estás usando docker localmente ingresa al contenedor usando: `docker exec -it helpdesk_django /bin/bash`*):

1. Ingresa a la consola shell de Django:
```bash
python manage.py shell
```

2. Estando dentro del entorno Python importa la rutina y ejecuta:
```python
from helpdesk.ml.train_model import train_model
train_model()
quit()
```

Esto generará un archivo `helpdesk/ml/model.pkl` que servirá de "Cerebro" de ahí en adelante.

### Usar el Servicio Analítico

Ingresa nuevamente a `http://localhost:8000/equipos/` desde el panel de **Equipos** dando inicio de sesión con el administrador e inspecciona la tabla de registros. Notarás un nuevo botón denominado `Analizar IA` a nivel de fila.
Haz click para acceder de forma instántanea a la evaluación general y nivel de riesgo estimado para ese dispositivo específico.
