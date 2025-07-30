from django.urls import path
from crawler import views
from panel.views import index

app_name = 'crawler'

urlpatterns = [
    # Dashboard principal
    path('', views.crawler_dashboard, name='dashboard'),
    # path('', views.index, name='dashboard'),

    # Gestión de sesiones
    path('sesiones/', views.session_list, name='session_list'),
    path('sesiones/nuevo/', views.create_session, name='create_session'),
    # path('sesiones/nuevo/', views.start_new_session, name='start_new_session'),
    path('sesiones/<int:pk>/', views.session_detail, name='session_detail'),
    path('sesiones/<int:pk>/iniciar/', views.start_session, name='start_session'),
    path('sesiones/<int:pk>/detener/', views.stop_session, name='stop_session'),
    path('sesiones/<int:pk>/eliminar/', views.delete_session, name='delete_session'),

    # Vistas de sesión específicas
    path('sesiones/<int:pk>/resultados/', views.session_results, name='session_results'),
    path('sesiones/<int:pk>/logs/', views.session_logs, name='session_logs'),
    path('sesiones/<int:pk>/urls/', views.session_urls, name='session_urls'),

    # Progreso y monitoreo
    path('sesiones/<int:pk>/progreso/', views.session_progress, name='session_progress'),

    # Exportar datos
    path('sesiones/<int:pk>/exportar/', views.export_results, name='export_results'),

    # Acciones en lote
    path('actiones_en_lote/', views.bulk_actions, name='bulk_actions'),

    # Estadísticas
    path('estadisticas/', views.crawler_stats, name='stats'),

    # API endpoints
    path('api/sesiones/<int:pk>/status/', views.api_session_status, name='api_session_status'),
    path('api/dashboard/estadisticas/', views.api_dashboard_stats, name='api_dashboard_stats'),

    # Metadatos
    path('archivo/<int:result_id>/metadatos/', views.file_metadata_detail, name='file_metadata_detail'),
    path('sesiones/<int:pk>/metadatos-resumen/', views.session_metadata_summary, name='session_metadata_summary'),

    # Análisis avanzado
    path('sesiones/<int:pk>/analisis-avanzado/', views.session_advanced_analysis, name='session_advanced_analysis'),

]
