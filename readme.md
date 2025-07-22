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

## Datos de contexto

_Datos de contexto para el uso del sitio web_


### Acceso a sección de administración de Django

- [http://localhost:8000/admin/](http://localhost:8000/admin/)

- Usuario: `admin4`
- Password: `asdf.1234`

- Usuario: `gabo`
- Password: `asdf.1234`


### Funcionalidades

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


## Autor ✒️

* **[Gabo Araya](https://github.com/Gabo-araya/)** - *Backend y documentación*
