from django.shortcuts import render, redirect, get_object_or_404
# from django.http import HttpResponse
from django.http import request
from django.urls import reverse
from urllib.parse import urlencode
# from django.db.models import Q      #para búsquedas


# importación de funcionalidad para login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from allauth.account.utils import send_email_confirmation
from panel.forms import ProfileForm, EmailForm
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages


# importar utils
from panel.decorators import authenticated_user, allowed_users
from panel.utils import info_header_user, user_group, is_admin

# Importar modelos desde apps de backend
from panel.models import Profile_Model

# Importación de forms
from django import forms
from panel.forms import UserCreateForm, UserUpdateForm



#=======================================================================================================================================
# Login
#=======================================================================================================================================

def salir(request, *args, **kwargs):
    logout(request)
    return redirect('entrar')


@authenticated_user
def entrar(request, *args, **kwargs):
    '''Página de Login de la plataforma. Redirección de usuarios a Dashboard por tipo de usuario.'''
    # Sacar al usuario que ingresa a esta vista
    # logout(request)

    # Mensajes para el usuario
    status = ''

    if request.method == 'POST':
        form = AuthenticationForm(request, data = request.POST)

        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect('index')
            else:
                base_url = reverse('entrar')
                query_string =  urlencode({'status': 'ERROR'})
                url = '{}?{}'.format(base_url, query_string)
                return redirect(url)
                # return redirect('entrar')
        else:
            base_url = reverse('entrar')
            query_string =  urlencode({'status': 'ERROR'})
            url = '{}?{}'.format(base_url, query_string)
            return redirect(url)
            # return redirect('entrar')

    if request.method == 'GET':
        status_get = request.GET.get('status')
        print(f'status_get: {status_get}')
        if status_get == 'ERROR':
            status = 'ERROR'

        status_get = request.GET.get('status')
        print(f'status_get: {status_get}')
        if status_get == 'SALIR':
            status = 'SALIR'

    form = AuthenticationForm()

    context = {
        'page': 'Acceso / Login',
        'status': status,
        'form': form,
    }


    return render(request, 'login/login.html', context)


@login_required(login_url='entrar')
def index(request, *args, **kwargs):
    '''Redirecciona a la página de inicio de cada tipo de usuario.'''

    user_group = request.user.groups.first().name
    print(user_group)

    if user_group == 'admin':
        # return render(request, 'panel/dashboard_admin.html', context)
        return redirect('dashboard_admin')
    elif user_group == 'crawler':
        # return render(request, 'panel/dashboard_crawler.html', context)
        return redirect('dashboard_crawler')
    else:
        # return render(request, 'panel/dashboard_viewer.html', context)
        return redirect('dashboard_viewer')



#=======================================================================================================================================
# Vistas de redirección de usuarios a Dashboard
#=======================================================================================================================================

@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin'])
def dashboard_admin(request, *args, **kwargs):
    '''dashboard_admin'''
    info_user = info_header_user(request)
    context = {
        'page' : 'Dashboard Admin',
        'icon' : 'bi bi-grid',
        'info_user': info_user,
    }
    return render(request, 'panel/dashboard_admin.html', context)



@login_required(login_url='entrar')
@allowed_users(allowed_roles=['crawler'])
def dashboard_crawler(request, *args, **kwargs):
    '''dashboard_crawler'''
    info_user = info_header_user(request)
    context = {
        'page' : 'Dashboard Crawler',
        'icon' : 'bi bi-grid',
        'info_user': info_user,
    }
    return render(request, 'panel/dashboard_crawler.html', context)



@login_required(login_url='entrar')
@allowed_users(allowed_roles=['viewer'])
def dashboard_viewer(request, *args, **kwargs):
    '''dashboard_viewer'''
    info_user = info_header_user(request)
    context = {
        'page' : 'Dashboard Viewer',
        'icon' : 'bi bi-grid',
        'info_user': info_user,
    }
    return render(request, 'panel/dashboard_viewer.html', context)



#=======================================================================================================================================
# Vistas Dashboard ADMIN
#=======================================================================================================================================



#=======================================================================================================================================
# Vistas Dashboard CRAWLER
#=======================================================================================================================================



#=======================================================================================================================================
# Vistas Dashboard VIEWER
#=======================================================================================================================================






#=======================================================================================================================================
# Vistas para Gestión de Usuarios
#=======================================================================================================================================

@login_required(login_url='entrar') # Requiere autenticación
# @user_passes_test(is_admin, login_url='entrar') # Redirige si no es admin
@allowed_users(allowed_roles=['admin'])
def listar_usuarios(request):
    '''Lista todos los usuarios y sus grupos.'''
    users = User.objects.all().order_by('username')
    users_with_groups = []
    for user in users:
        groups = [group.name for group in user.groups.all()]

        # Añadir más información del perfil
        try:
            profile = Profile_Model.objects.get(user=user)
        except Profile_Model.DoesNotExist:
            profile = None # Manejar usuarios sin perfil si es posible

        users_with_groups.append({
            'user': user,
            'groups': ', '.join(groups) if groups else 'Ninguno',
            'profile': profile,
        })

    info_user = info_header_user(request)
    # print(info_user.id)

    context = {
        'page' : 'Usuarios',
        'icon' : 'bi bi-grid',
        'info_user': info_user,

        'singular': 'usuario',
        'plural': 'usuarios',
        'url_listar': 'listar_usuarios',
        'url_crear': 'crear_usuario',
        'url_ver': 'ver_usuario',
        'url_editar': 'modificar_usuario',
        'url_eliminar': 'eliminar_usuario',
        # 'success_create': success_create,
        # 'success_edit': success_edit,
        # 'success_delete': success_delete,
        'users': users_with_groups,
    }
    return render(request, 'panel/listar_usuarios.html', context)



@login_required(login_url='entrar') # Requiere autenticación
# @user_passes_test(is_admin, login_url='entrar') # Redirige si no es admin
@allowed_users(allowed_roles=['admin'])
def crear_usuario(request):
    '''Agrega un nuevo usuario y lo asigna a un grupo.'''
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            group_name = form.cleaned_data['group_name']

            # Crea el usuario manualmente
            user = User.objects.create_user(username=username, email=email, password=password)

            # Asigna al grupo seleccionado
            if group_name:
                group, created = Group.objects.get_or_create(name=group_name)
                user.groups.add(group)

            # Crea un perfil vacío para el nuevo usuario
            try: # Usar un try-except para manejar si Profile_Model ya existe o falla
                Profile_Model.objects.create(user=user)
            except Exception as e:
                # Manejar el error si el perfil ya existe o no se pudo crear por alguna razón
                messages.warning(request, f'Usuario {user.username} creado, pero no se pudo crear el perfil: {e}')

            messages.success(request, f'Usuario {user.username} creado exitosamente y asignado a {group_name}.')
            return redirect('listar_usuarios')
    else:
        form = UserCreateForm()

    info_user = info_header_user(request)
    context = {
        'page' : 'Crear Usuario',
        'icon' : 'bi bi-grid',
        'info_user': info_user,
        'singular': 'usuario',
        'plural': 'usuarios',
        'url_listar': 'listar_usuarios',
        'url_crear': 'crear_usuario',
        'url_ver': 'ver_usuario',
        'url_editar': 'modificar_usuario',
        'url_eliminar': 'eliminar_usuario',
        'form': form,
        'action': 'Crear',
    }
    return render(request, 'panel/generic_form.html', context)



@login_required(login_url='entrar') # Requiere autenticación
# @user_passes_test(is_admin, login_url='entrar') # Redirige si no es admin
@allowed_users(allowed_roles=['admin'])
def modificar_usuario(request, user_id):
    '''Edita un usuario existente y cambia su grupo.'''
    user = get_object_or_404(User, pk=user_id)
    # Obtener el nombre del grupo actual del usuario (el primero, si tiene varios)
    current_group_name = user.groups.first().name if user.groups.exists() else ''

    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()

            # Actualiza el grupo del usuario
            new_group_name = form.cleaned_data['group_name']
            if new_group_name != current_group_name: # Solo si el grupo ha cambiado
                user.groups.clear() # Limpia los grupos actuales
                if new_group_name:
                    group, created = Group.objects.get_or_create(name=new_group_name)
                    user.groups.add(group)

            messages.success(request, f'Usuario {user.username} actualizado exitosamente.')
            return redirect('listar_usuarios')
    else:
        # Inicializa el formulario con el grupo actual del usuario
        form = UserUpdateForm(instance=user, initial={'group_name': current_group_name})

    info_user = info_header_user(request)
    context = {
        'page' : 'Modificar Usuario',
        'icon' : 'bi bi-grid',
        'info_user': info_user,

        'singular': 'usuario',
        'plural': 'usuarios',
        'url_listar': 'listar_usuarios',
        'url_crear': 'crear_usuario',
        'url_ver': 'ver_usuario',
        'url_editar': 'modificar_usuario',
        'url_eliminar': 'eliminar_usuario',
        # 'success_create': success_create,
        # 'success_edit': success_edit,
        # 'success_delete': success_delete,
        'form': form,
        'action': 'Editar',
    }
    return render(request, 'panel/generic_form.html', context)



@login_required(login_url='entrar') # Requiere autenticación
# @user_passes_test(is_admin, login_url='entrar') # Redirige si no es admin
@allowed_users(allowed_roles=['admin'])
def cambiar_password_usuario(request, user_id):
    '''Cambia la contraseña de un usuario específico.'''
    target_user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        form = PasswordChangeForm(target_user, request.POST)
        if form.is_valid():
            user = form.save()
            # update_session_auth_hash(request, user) # Solo si es para el usuario logueado
            messages.success(request, f'Contraseña para {target_user.username} cambiada exitosamente.')
            return redirect('listar_usuarios')
    else:
        form = PasswordChangeForm(target_user)

    info_user = info_header_user(request)
    context = {
        'page' : 'Cambiar Contraseña',
        'icon' : 'bi bi-grid',
        'info_user': info_user,

        'singular': 'usuario',
        'plural': 'usuarios',
        'url_listar': 'listar_usuarios',
        'url_crear': 'crear_usuario',
        'url_ver': 'ver_usuario',
        'url_editar': 'modificar_usuario',
        'url_eliminar': 'eliminar_usuario',
        # 'success_create': success_create,
        # 'success_edit': success_edit,
        # 'success_delete': success_delete,
        'form': form,
        'target_user': target_user
    }
    return render(request, 'panel/change_password_form.html', context)



@login_required(login_url='entrar') # Requiere autenticación
# @user_passes_test(is_admin, login_url='entrar') # Redirige si no es admin
@allowed_users(allowed_roles=['admin'])
def eliminar_usuario(request, user_id):
    '''Elimina un usuario.'''
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'Usuario {username} eliminado exitosamente.')
        return redirect('listar_usuarios')

    info_user = info_header_user(request)
    context = {
        'page' : 'Cambiar Contraseña',
        'icon' : 'bi bi-grid',
        'info_user': info_user,
        'singular': 'usuario',
        'plural': 'usuarios',
        'url_listar': 'listar_usuarios',
        'url_crear': 'crear_usuario',
        'url_ver': 'ver_usuario',
        'url_editar': 'modificar_usuario',
        'url_eliminar': 'eliminar_usuario',
        'item': user,
    }
    return render(request, 'panel/generic_delete_object.html', context)




#=======================================================================================================================================
# Vistas para Perfil de Usuario
#=======================================================================================================================================

@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin'])
def ver_perfil(request, username=None):
    if username:
        profile = get_object_or_404(User, username=username).profile_model
    else:
        try:
            profile = request.user.profile_model
        except:
            return redirect('salir')

    #print(request.user.profile_model)
    context = {
        'profile': profile
    }
    return render(request, 'panel/profile.html', context)


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin'])
def modificar_perfil(request):
    form = ProfileForm(instance=request.user.profile_model)

    if request.method =='POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile_model)
        if form.is_valid():
            form.save()
            return redirect('ver_perfil')

    if request.path == reverse('agregar_perfil'):
        onboarding = True
    else:
        onboarding = False

    context = {
        'form': form,
        'onboarding': onboarding,
    }

    return render(request, 'panel/profile_edit.html',context)



@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin'])
def configuracion_perfil(request):
    return render(request, 'panel/profile_settings.html')



@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin','crawler','viewer'])
def cambiar_email_perfil(request):

    if request.htmx:
        form = EmailForm(instance=request.user)
        context = {
            'form': form,
        }
        return render(request, 'partials/email_form.html', context)

    if request.method == 'POST':
        form = EmailForm(request.POST, instance=request.user)

        if form.is_valid():

            # Check if the email already exists
            email = form.cleaned_data['email']
            if User.objects.filter(email=email).exclude(id=request.user.id).exists():
                messages.warning(request, f'{email} ya está en uso.')
                return redirect('configuracion_perfil')

            form.save()
            # Then signal updates email address and set verified to false
            # Then send confirmation email
            send_email_confirmation(request, request.user)

            return redirect('configuracion_perfil')
        else:
            messages.warning(request, 'Formato no válido')
            return redirect('configuracion_perfil')

    return redirect('home')



@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin','crawler','viewer'])
def verificar_email_perfil(request):
    send_email_confirmation(request, request.user)
    return redirect('configuracion_perfil')



@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin'])
def eliminar_perfil(request):
    user = request.user
    if request.method == 'POST':
        logout(request)
        user.delete()
        messages.success(request, 'Account deleted, what a pity!')
        return redirect('home')

    return render(request, 'panel/profile_delete.html')






#=======================================================================================================================================
# Otras URLS
#=======================================================================================================================================


@login_required(login_url='entrar')
def test(request, *args, **kwargs):
    '''Test'''
    info_user = info_header_user(request)
    context = {
        'page' : 'Login',
        #'object_list': object_list,
        'info_user': info_user,
    }
    return render(request, 'panel/error_404.html', context)
    # return render(request, 'login/register_user.html', context)



@login_required(login_url='entrar')
def configuracion(request, *args, **kwargs):
    '''Configuración'''

    info_user = info_header_user(request)

    context = {
        'page' : 'Configuración',
        #'object_list': object_list,
        'info_user': info_user,
    }
    return render(request, 'panel/configuracion.html', context)



@login_required(login_url='entrar')
def ayuda(request, *args, **kwargs):
    '''Ayuda'''

    info_user = info_header_user(request)

    context = {
        'page' : 'Ayuda',
        #'object_list': object_list,
        'info_user': info_user,
    }
    return render(request, 'panel/ayuda.html', context)



@login_required(login_url='entrar')
def blank(request, *args, **kwargs):
    '''Blank'''

    # Ejemplo de lista de usuarios
    users = User.objects.all().order_by('username')
    users_with_groups = []
    for user in users:
        groups = [group.name for group in user.groups.all()]

        # Añadir más información del perfil
        try:
            profile = Profile_Model.objects.get(user=user)
        except Profile_Model.DoesNotExist:
            profile = None # Manejar usuarios sin perfil si es posible

        users_with_groups.append({
            'user': user,
            'groups': ', '.join(groups) if groups else 'Ninguno',
            'profile': profile,
        })

    info_user = info_header_user(request)

    context = {
        'page' : 'Blank',

        'icon' : 'bi bi-grid',
        'info_user': info_user,

        'singular': 'usuario',
        'plural': 'usuarios',
        'url_listar': 'listar_usuarios',
        'url_crear': 'crear_usuario',
        'url_ver': 'ver_usuario',
        'url_editar': 'modificar_usuario',
        'url_eliminar': 'eliminar_usuario',
        # 'success_create': success_create,
        # 'success_edit': success_edit,
        # 'success_delete': success_delete,
        'users': users_with_groups,
    }
    return render(request, 'panel/blank.html', context)
