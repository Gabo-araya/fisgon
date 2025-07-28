# Fisgón - Web crawler de metadatos.

_Web crawler de metadatos con sistema de login simple con funcionalidad de verificación de usuarios._

Estas instrucciones te permitirán obtener una copia del proyecto en funcionamiento en tu máquina local para propósitos de desarrollo y pruebas.

## Pre-requisitos

_Esta es una lista de los paquetes que deben estar instalados previamente:_

* Python 3
	- Lenguaje de programación
	- [Ayuda - https://docs.microsoft.com/en-us/windows/python/beginners)](https://docs.microsoft.com/en-us/windows/python/beginners)
	- [Curso Django desde Cero en youtube](https://www.youtube.com/watch?v=vo4VF3neyrs)

* Pip
	- Gestor de instalación de paquetes PIP
	- [Ayuda - https://tecnonucleous.com/2018/01/28/como-instalar-pip-para-python-en-windows-mac-y-linux/](https://tecnonucleous.com/2018/01/28/como-instalar-pip-para-python-en-windows-mac-y-linux/)

* Virtualenv
	- Creador de entornos virtuales para Python
	- [Ayuda - https://techexpert.tips/es/windows-es/instalacion-del-entorno-virtual-de-python-en-windows/](https://techexpert.tips/es/windows-es/instalacion-del-entorno-virtual-de-python-en-windows/)

### Instalación pre-requisitos (Windows) 🔧

Muchas veces tenemos ese problema común de no poder instalar ciertas librerías o realizar configuraciones para poder desarrollar en Windows para Web y es por ello que en éste tutorial vamos a ver los pasos para instalar Python y configurarlo con Pip y Virtualenv para así poder empezar a desarrollar aplicaciones basadas en éste lenguaje e instalar Django para crear aplicaciones web. [Ver video -> **https://www.youtube.com/watch?v=sG7Q-r_SZhA**](https://www.youtube.com/watch?v=sG7Q-r_SZhA)

1. Descargamos e instalamos Python 3.6 (o una versión superior) para Windows
	- [https://www.python.org/downloads/](https://www.python.org/downloads/)

2. Agregaremos Python a las variables de entorno de nuestro sistema si es que no se agregaron durante la instalación para que así podamos ejecutarlo desde la terminal `/cmd`
	- `C:\Python34 y C:\Python34\Scripts`

3. Ejecutamos Pip para verificar que esté instalado correctamente y también la versión
	- `pip --version`

4. Instalamos Virtualenv con
	- `pip install virtualenv`

5. Verificamos la versión de Virtualenv
	- `virtualenv --version`

6. Crearemos un entorno virtual con Python
	- `virtualenv test`

7. Iniciamos el entorno virtual
	- `.\test\Scripts\activate`

8. Finalmente desactivamos el entorno virtual
	- `deactivate`

## Instalación pre-requisitos (GNU/Linux) 🔧

1. Ejecutamos Pip para verificar que esté instalado correctamente
	- `pip3 --version`

2. Instalamos Virtualenv con pip
	- `pip3 install virtualenv`

3. Verificamos la versión de Virtualenv
	- `virtualenv --version`

4. Crearemos un entorno virtual con Python
	- `python3 -m venv /home/gabo/envs/gaboaraya/env`

5. Activamos el entorno virtual
	- `source /home/gabo/envs/gaboaraya/env/bin/activate`

6. Finalmente desactivamos el entorno virtual
	- `deactivate`

### Instalación Local

Seguir los siguientes pasos para la instalación local.

1. Clonar el repositorio o subir/descargar los archivos.

	- `git clone https://github.com/Gabo-araya/fisgon-web-crawler.git`

2. Instalar los requerimientos.

	- `python3 -m pip install -r requirements.txt`

3. Revisar settings.py y .env
	- Revisar que la sección de base de datos esté configurada para que trabaje con la base de datos SQLite en local.

4. Realizar migraciones
	- Crear archivos de migración: `python3 manage.py makemigrations`
	- Realizar migraciones`python3 manage.py migrate`

5. Crear superusuario
	- `python3 manage.py createsuperuser`
	- Si se usa Cpanel es necesario indicar el encoding primero vía terminal:
		-`export PYTHONIOENCODING="UTF-8"; python3.6 manage.py createsuperuser`

6. Obtener archivos estáticos
	- `python3 manage.py collectstatic`

7. Iniciar el servidor
	- `python3 manage.py runserver`
	- Iniciar en un puerto específico (8000):`python3 manage.py runserver 8000`




### Ejemplo de archivo `.env`

```
# .env
DEBUG=True

SECRET_KEY=clave-secreta-aqui

DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1

# Configuración de Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Configuración del Crawler
CRAWLER_USER_AGENT=FisgonCrawler/1.0
CRAWLER_MAX_DEPTH=5
CRAWLER_RATE_LIMIT=1.0

# Configuración de la base de datos (puedes ponerla aquí o en un solo string)
# DB_NAME=fisgon_db
# DB_USER=django_user
# DB_PASSWORD=una_contraseña_segura
# DB_HOST=localhost
# DB_PORT=5432

```


### Crear Usuarios y Grupos
```bash
# Abrir shell de Django
python manage.py shell
```

```
# Dentro del shell de Django:
from django.contrib.auth.models import User, Group

# Crear grupos
admin_group = Group.objects.create(name='admin')
crawler_group = Group.objects.create(name='crawler')
viewer_group = Group.objects.create(name='viewer')

# Crear usuarios de prueba
# Usuario crawler
crawler_user = User.objects.create_user(
    username='crawler',
    email='crawler@example.com',
    password='asdf.1234'
)
crawler_user.groups.add(crawler_group)

# Usuario viewer
viewer_user = User.objects.create_user(
    username='viewer',
    email='viewer@example.com',
    password='asdf.1234'
)
viewer_user.groups.add(viewer_group)

# Asignar el superusuario al grupo admin
admin_user = User.objects.get(username='admin')  # Reemplazar con tu username
admin_user.groups.add(admin_group)

exit()
```



### Recolectar Archivos Estáticos

```
# Crear directorio static si no existe
mkdir -p staticfiles

# Recolectar archivos estáticos
python manage.py collectstatic --noinput
```






## Flujo de Trabajo Completo

### **1. Proceso de Crawling (Descubrimiento)**

```
Usuario configura target → Crawler inicia → Descubre URLs → Filtra por tipo → Queue de procesamiento
```

**Detalles del proceso:**

1. **Configuración inicial**:
   - Usuario define dominio objetivo (ej: `example.com`)
   - Establece profundidad máxima (niveles de recursión)
   - Define tipos de archivo de interés
   - Configura rate limiting (requests/segundo)

2. **Descubrimiento de URLs**:
   - Inicia con robots.txt y sitemap.xml
   - Rastrea links HTML recursivamente
   - Identifica archivos por extensión
   - Usa técnicas como directory bruteforcing suave
   - Almacena URLs encontradas en cola Redis

3. **Filtrado inteligente**:
   - Elimina duplicados
   - Filtra por tamaño de archivo (evita archivos gigantes)
   - Prioriza por tipo de archivo (PDFs > Imágenes > Multimedia)
   - Respeta blacklists y whitelist definidas

### **2. Proceso de Extracción (Harvesting)**

```
URL → Descarga → Identificación de tipo → Extractor específico → Metadatos estructurados
```

**Por cada archivo encontrado:**

1. **Descarga controlada**:
   - Verificación de Content-Type
   - Límite de tamaño (ej: máximo 50MB)
   - Timeout configurable
   - Manejo de errores HTTP

2. **Identificación precisa**:
   - Magic numbers (primeros bytes del archivo)
   - Extensión vs contenido real
   - Validación de formato

3. **Extracción especializada**:

   **Para PDFs:**
   ```
   Archivo PDF → PyPDF2/pdfplumber →
   {
     'author': 'Juan Pérez',
     'creator': 'Microsoft Word',
     'creation_date': '2023-05-15',
     'modification_date': '2023-05-16',
     'title': 'Informe Confidencial',
     'subject': 'Análisis Financiero Q2',
     'producer': 'Adobe Acrobat',
     'pdf_version': '1.4'
   }
   ```

   **Para Imágenes:**
   ```
   Imagen JPEG → ExifRead/Pillow →
   {
     'camera_make': 'Canon',
     'camera_model': 'EOS R5',
     'datetime_original': '2023-05-15 14:30:22',
     'gps_coordinates': '(lat: -33.4489, lon: -70.6693)',
     'software': 'Adobe Lightroom 6.0',
     'artist': 'Fotógrafo Profesional',
     'copyright': '© Empresa XYZ 2023'
   }
   ```

   **Para Office:**
   ```
   Word Doc → python-docx →
   {
     'author': 'Maria González',
     'last_modified_by': 'Pedro Silva',
     'created': '2023-05-10',
     'modified': '2023-05-15',
     'company': 'Empresa Confidencial SA',
     'manager': 'Director TI',
     'revision': '5',
     'template': 'plantilla_corporativa.dotx'
   }
   ```

### **3. Proceso de Análisis (Intelligence)**

```
Metadatos → Normalización → Análisis de patrones → Scoring de riesgo → Alertas
```

**Análisis multinivel:**

1. **Normalización de datos**:
   - Estandarización de fechas
   - Limpieza de nombres (quitar acentos, mayúsculas)
   - Categorización de software
   - Geocodificación de coordenadas GPS

2. **Detección de patrones**:

   **Usuarios frecuentes:**
   ```python
   # Ejemplo de patrón detectado
   {
     'pattern_type': 'frequent_author',
     'value': 'juan.perez@empresa.com',
     'occurrences': 47,
     'risk_score': 8.5,
     'file_types': ['pdf', 'docx', 'xlsx'],
     'date_range': '2023-01-15 to 2023-05-20'
   }
   ```

   **Software desactualizado:**
   ```python
   {
     'pattern_type': 'outdated_software',
     'software': 'Adobe Acrobat 9.0',
     'version_year': 2008,
     'risk_score': 9.2,
     'vulnerability_count': 23,
     'affected_files': 12
   }
   ```

   **Información geográfica:**
   ```python
   {
     'pattern_type': 'location_exposure',
     'coordinates': [(-33.4489, -70.6693), (-33.4512, -70.6580)],
     'location_cluster': 'Santiago Centro, Chile',
     'risk_score': 7.8,
     'files_with_gps': 8
   }
   ```

### **4. Proceso de Almacenamiento (Persistencia)**

```
Metadatos → Validación → Base de datos → Indexación → API de consulta
```

**Estructura de datos propuesta:**

```sql
-- Tabla principal de crawling sessions
crawl_sessions (
    id, user_id, target_domain, status,
    started_at, completed_at, total_files_found
)

-- URLs descubiertas
discovered_urls (
    id, session_id, url, file_type, file_size,
    status, discovered_at, processed_at
)

-- Metadatos extraídos
extracted_metadata (
    id, url_id, metadata_type, field_name,
    field_value, confidence_score, extracted_at
)

-- Patrones detectados
detected_patterns (
    id, session_id, pattern_type, description,
    risk_score, affected_files_count, details_json
)
```

### **5. Proceso de Visualización (Dashboard)**

```
Datos → Agregación → APIs → Frontend → Visualizaciones interactivas
```

**Tipos de visualización:**

1. **Dashboard principal**:
   - Métricas en tiempo real (archivos procesados, patrones detectados)
   - Timeline de actividad del crawl
   - Top 10 autores más frecuentes
   - Mapa de calor de tipos de archivo

2. **Análisis detallado**:
   - Gráfico de red de relaciones autor-documento
   - Timeline de versiones de software
   - Mapa geográfico de coordenadas GPS
   - Análisis de riesgo por categoría

3. **Reportes exportables**:
   - PDF ejecutivo con hallazgos principales
   - CSV detallado para análisis técnico
   - Recomendaciones de mitigación




### Funcionalidades activas

- Creación de usuario (User)
- Completitud de campos asociados de usuario (Onboarding)
- Modificación de settings
- Modificación de correo electrónico
- Validación de correo electrónico
- Eliminación de usuario
- Inicio de sesión de usuario
- Cierre de sesión de usuario




## Herramientas de construcción

_Estas son las herramientas que se han utilizado en este proyecto_

* [Django](https://www.djangoproject.com/) - El framework web usado

### Acceso a sección de administración de Django

- [http://localhost:8000/admin/](http://localhost:8000/admin/)

- Usuario: `admin4`
- Password: `asdf.1234`
- Tipo: `admin`

- Usuario: `gabo`
- Password: `asdf.1234`
- Tipo: `admin`

- Usuario: `crawler`
- Password: `asdf.1234`
- Tipo: `crawler`

- Usuario: `viewer`
- Password: `asdf.1234`
- Tipo: `viewer`


## Autor ✒️

* **[Gabo Araya](https://github.com/Gabo-araya/)** - *Backend y documentación*
