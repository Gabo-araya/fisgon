from django.urls import path, include
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.i18n import JavaScriptCatalog

import panel.views
# from panel.views import *

urlpatterns = [
#dashboard
    path('', panel.views.index, name='index'),
    # path('dashboard_admin/', panel.views.dashboard_admin, name='dashboard_admin'),
    # path('dashboard_crawler/', panel.views.dashboard_crawler, name='dashboard_crawler'),
    # path('dashboard_viewer/', panel.views.dashboard_viewer, name='dashboard_viewer'),
    path('configuracion/', panel.views.configuracion, name='configuracion'),
    path('ayuda/', panel.views.ayuda, name='ayuda'),

#perfil
    path('ver_perfil/', panel.views.ver_perfil, name='ver_perfil'), # name='profile'
    path('modificar_perfil/', panel.views.modificar_perfil, name='modificar_perfil'), #name='profile-edit'

    path('agregar_perfil/', panel.views.modificar_perfil, name='agregar_perfil'), #name='profile-onboarding'
    path('configuracion_perfil/', panel.views.configuracion_perfil, name='configuracion_perfil'), #name='profile-settings'
    path('eliminar_perfil/', panel.views.eliminar_perfil, name='eliminar_perfil'), #name='profile-delete'

    # htmx
    path('cambiar_email_perfil/', panel.views.cambiar_email_perfil, name='cambiar_email_perfil'), #name='profile-emailchange'
    path('verificar_email_perfil/', panel.views.verificar_email_perfil, name='verificar_email_perfil'), #name='profile-emailverify'

#JS-Catalog para mostrar widget admin para fechas y horas
    path('jsi18n', JavaScriptCatalog.as_view(), name='js-catalog'),

#=======================================================================================================================================
# Login
#=======================================================================================================================================

    path('test/', panel.views.test, name='test'),
    path('blank/', panel.views.blank, name='blank'),

    path('login/', panel.views.entrar, name='login'),
    path('entrar/', panel.views.entrar, name='entrar'),
    path('salir/', panel.views.salir, name='salir'),



#=======================================================================================================================================
# Gestión de usuarios
#=======================================================================================================================================

    path('usuarios/', panel.views.listar_usuarios, name='listar_usuarios'), # user_list
    path('usuarios/crear/', panel.views.crear_usuario, name='crear_usuario'), # user_create
    path('usuarios/modificar/<int:user_id>/', panel.views.modificar_usuario, name='modificar_usuario'), # user_edit
    path('usuarios/cambiar_password/<int:user_id>/', panel.views.cambiar_password_usuario, name='cambiar_password_usuario'), # user_change_password
    path('usuarios/eliminar/<int:user_id>/', panel.views.eliminar_usuario, name='eliminar_usuario'), # user_delete



#=======================================================================================================================================
# Reset de password
#=======================================================================================================================================

    # path('reset_password/', auth_views.PasswordResetView.as_view(template_name='login/password_reset.html'),
    #     name='reset_password'),
    # path('reset_password_enviado/', auth_views.PasswordResetDoneView.as_view(template_name='login/password_reset_sent.html'),
    #     name='password_reset_done'),
    # path('reset_password_confirmado/<uidb64>/<token>', auth_views.PasswordResetConfirmView.as_view(template_name='login/password_reset_form.html'),
    #     name='password_reset_confirm'),
    # path('reset_password_completado/', auth_views.PasswordResetCompleteView.as_view(template_name='login/password_reset_done.html'),
    #     name='password_reset_complete'),


] # fin urlpatterns
