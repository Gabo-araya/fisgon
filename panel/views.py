from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, request
from django.urls import reverse
from urllib.parse import urlencode
from django.db.models import Q      #para búsquedas


# importación de funcionalidad para login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from allauth.account.utils import send_email_confirmation
from panel.forms import ProfileForm, EmailForm
from django.contrib.auth.models import User
from django.contrib import messages


# importar utils
from panel.decorators import authenticated_user, allowed_users
from panel.utils import info_header_user, user_group

# Importar modelos desde apps de backend
from panel.models import Profile_Model

# Importación de forms




#=======================================================================================================================================
# Login
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


def salir(request, *args, **kwargs):
    logout(request)
    return redirect('entrar')


@authenticated_user
def entrar(request, *args, **kwargs):
    '''Página de Login de la plataforma. '''
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
    '''Lista de elementos con las que se pueden realizar acciones.'''

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
# Vistas para Perfil de Usuario
#=======================================================================================================================================
@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin','crawler','viewer'])
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


@login_required
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


@login_required
def configuracion_perfil(request):
    return render(request, 'panel/profile_settings.html')


@login_required
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


@login_required
def verificar_email_perfil(request):
    send_email_confirmation(request, request.user)
    return redirect('configuracion_perfil')



@login_required
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
    info_user = info_header_user(request)
    context = {
        'page' : 'Blank',
        'info_user': info_user,
    }
    return render(request, 'panel/blank.html', context)
