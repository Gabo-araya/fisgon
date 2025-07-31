import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_http_methods
import json

from panel.decorators import allowed_users
from panel.utils import info_header_user

from .models import CrawlSession, URLQueue, CrawlResult, CrawlLog
from .forms import CreateCrawlSessionForm, CrawlSessionFilterForm, BulkActionForm
from .tasks import start_crawl_session, stop_crawl_session


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler, viewer'])
def crawler_dashboard(request):
    '''Dashboard principal del crawler'''

    return redirect('index')


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler'])
def crawler_dashboard_old(request):
    '''Dashboard principal del crawler'''

    # Estadísticas generales
    user_sessions = CrawlSession.objects.filter(user=request.user)

    stats = {
        'total_sessions': user_sessions.count(),
        'active_sessions': user_sessions.filter(status__in=['pending', 'running', 'paused']).count(),
        'completed_sessions': user_sessions.filter(status='completed').count(),
        'total_files_found': sum(session.total_files_found for session in user_sessions),
        'total_urls_processed': sum(session.total_urls_processed for session in user_sessions),
    }

    # Sesiones recientes
    recent_sessions = user_sessions.order_by('-created_at')[:5]

    # Sesiones activas
    active_sessions = user_sessions.filter(
        status__in=['pending', 'running', 'paused']
    ).order_by('-started_at')[:10]

    info_user = info_header_user(request)

    context = {
        'page': 'Dashboard Crawler',
        'icon': 'bi bi-incognito',
        'info_user': info_user,
        'stats': stats,
        'recent_sessions': recent_sessions,
        'active_sessions': active_sessions,
    }

    return render(request, 'crawler/dashboard_crawler.html', context)


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler'])
def create_session(request):
    '''Crear nueva sesión de crawling'''

    if request.method == 'POST':
        form = CreateCrawlSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.user = request.user
            session.save()

            messages.success(request, f'Sesión "{session.name}" creada exitosamente.')
            return redirect('crawler:session_detail', pk=session.pk)
    else:
        form = CreateCrawlSessionForm()

    info_user = info_header_user(request)

    context = {
        'page': 'Nueva Sesión de Crawling',
        'icon': 'bi bi-plus-circle',
        'info_user': info_user,
        'form': form,
    }

    return render(request, 'crawler/create_session.html', context)



@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler'])
def start_new_session(request):
    '''Crear e iniciar inmediatamente una nueva sesión de crawling'''
    if request.method == 'POST':
        try:
            # Obtener datos del JSON
            import json
            data = json.loads(request.body)

            # Crear nueva sesión
            session = CrawlSession.objects.create(
                name=data.get('name', f"Sesión {timezone.now().strftime('%Y-%m-%d %H:%M')}"),
                user=request.user,
                target_url=data.get('target_url'),
                target_domain=data.get('target_domain'),
                max_depth=data.get('max_depth', 3),
                rate_limit=data.get('rate_limit', 1.0),
                max_pages=data.get('max_pages', 1000),
                file_types=data.get('file_types', []),
                respect_robots_txt=data.get('respect_robots_txt', True),
                follow_redirects=data.get('follow_redirects', True),
                extract_metadata=data.get('extract_metadata', True),
            )

            # Iniciar crawling inmediatamente
            start_crawl_session.delay(session.id)

            return JsonResponse({
                'success': True,
                'session_id': session.id,
                'message': f'Sesión "{session.name}" creada e iniciada exitosamente'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)

    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)



@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler', 'viewer'])
def session_list(request):
    '''Lista de sesiones de crawling'''

    # Base queryset - los admins ven todo, otros solo sus sesiones
    if request.user.groups.filter(name='admin').exists():
        sessions = CrawlSession.objects.all()
    else:
        sessions = CrawlSession.objects.filter(user=request.user)

    # Aplicar filtros
    filter_form = CrawlSessionFilterForm(request.GET)
    if filter_form.is_valid():
        if filter_form.cleaned_data['status']:
            sessions = sessions.filter(status=filter_form.cleaned_data['status'])

        if filter_form.cleaned_data['domain']:
            sessions = sessions.filter(
                target_domain__icontains=filter_form.cleaned_data['domain']
            )

        if filter_form.cleaned_data['date_from']:
            sessions = sessions.filter(
                created_at__date__gte=filter_form.cleaned_data['date_from']
            )

        if filter_form.cleaned_data['date_to']:
            sessions = sessions.filter(
                created_at__date__lte=filter_form.cleaned_data['date_to']
            )

        if filter_form.cleaned_data['user']:
            sessions = sessions.filter(
                user__username__icontains=filter_form.cleaned_data['user']
            )

    # Ordenar
    sessions = sessions.order_by('-created_at')

    # Paginación
    paginator = Paginator(sessions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    info_user = info_header_user(request)

    context = {
        'page': 'Sesiones de Crawling',
        'icon': 'bi bi-list-ul',
        'info_user': info_user,
        'page_obj': page_obj,
        'filter_form': filter_form,
        'total_sessions': sessions.count(),
    }

    return render(request, 'crawler/session_list.html', context)


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler', 'viewer'])
def session_detail(request, pk):
    '''Detalle de una sesión de crawling'''

    session = get_object_or_404(CrawlSession, pk=pk)

    # Verificar permisos
    if not request.user.groups.filter(name='admin').exists() and session.user != request.user:
        messages.error(request, 'No tienes permisos para ver esta sesión.')
        return redirect('crawler:session_list')

    # Estadísticas de la sesión
    url_stats = {
        'pending': session.url_queue.filter(status='pending').count(),
        'processing': session.url_queue.filter(status='processing').count(),
        'completed': session.url_queue.filter(status='completed').count(),
        'failed': session.url_queue.filter(status='failed').count(),
        'skipped': session.url_queue.filter(status='skipped').count(),
    }

    # URLs recientes
    recent_urls = session.url_queue.order_by('-processed_at')[:10]

    # Archivos encontrados recientes
    recent_files = session.results.order_by('-created_at')[:10]

    # Log reciente
    recent_logs = session.logs.order_by('-created_at')[:20]

    # Estadísticas por tipo de archivo
    file_type_stats = session.url_queue.filter(
        status='completed',
        url_type__in=session.get_file_types_list()
    ).values('url_type').annotate(count=Count('id')).order_by('-count')

    info_user = info_header_user(request)

    context = {
        'page': f'Sesión: {session.name}',
        'icon': 'bi bi-eye',
        'info_user': info_user,
        'session': session,
        'url_stats': url_stats,
        'recent_urls': recent_urls,
        'recent_files': recent_files,
        'recent_logs': recent_logs,
        'file_type_stats': file_type_stats,
    }

    return render(request, 'crawler/session_detail.html', context)


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler'])
def start_session(request, pk):
    '''Iniciar una sesión de crawling'''

    session = get_object_or_404(CrawlSession, pk=pk)

    # Verificar permisos
    if not request.user.groups.filter(name='admin').exists() and session.user != request.user:
        messages.error(request, 'No tienes permisos para iniciar esta sesión.')
        return redirect('crawler:session_detail', pk=pk)

    if session.status != 'pending':
        messages.warning(request, f'La sesión ya está en estado: {session.get_status_display()}')
        return redirect('crawler:session_detail', pk=pk)

    # Iniciar sesión de crawling
    try:
        start_crawl_session.delay(session.id)
        messages.success(request, f'Crawling iniciado para la sesión "{session.name}"')
    except Exception as e:
        messages.error(request, f'Error al iniciar crawling: {str(e)}')

    return redirect('crawler:session_detail', pk=pk)


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler'])
def stop_session(request, pk):
    '''Detener una sesión de crawling'''

    session = get_object_or_404(CrawlSession, pk=pk)

    # Verificar permisos
    if not request.user.groups.filter(name='admin').exists() and session.user != request.user:
        messages.error(request, 'No tienes permisos para detener esta sesión.')
        return redirect('crawler:session_detail', pk=pk)

    if session.status not in ['running', 'pending', 'paused']:
        messages.warning(request, f'No se puede detener una sesión en estado: {session.get_status_display()}')
        return redirect('crawler:session_detail', pk=pk)

    # Detener sesión
    try:
        stop_crawl_session.delay(session.id)
        messages.success(request, f'Sesión "{session.name}" detenida.')
    except Exception as e:
        messages.error(request, f'Error al detener sesión: {str(e)}')

    return redirect('crawler:session_detail', pk=pk)


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler'])
# @require_http_methods(["POST"])
def delete_session(request, pk):
    '''Eliminar una sesión de crawling'''

    session = get_object_or_404(CrawlSession, pk=pk)

    # Verificar permisos de acceso a la sesión
    if not request.user.groups.filter(name='admin').exists() and session.user != request.user:
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        # Redirige a una página segura, como la lista de sesiones.
        return redirect('crawler:session_list')

    # Si la petición es POST, se procesa la eliminación.
    if request.method == 'POST':
        # Validar que la sesión no esté en ejecución antes de eliminar.
        if session.status in ['running', 'processing']:
            messages.error(request, 'No se puede eliminar una sesión en ejecución. Detén la sesión primero.')
            return redirect('crawler:session_detail', pk=pk)

        session_name = session.name
        session.delete()
        messages.success(request, f'Sesión "{session_name}" eliminada exitosamente.')
        return redirect('crawler:session_list') # Redirigir a la lista de sesiones tras eliminar

    # Si la petición es GET, se muestra la página de confirmación.
    info_usuario = info_header_user(request)

    context = {
        'page' : 'Eliminar Sesión de Crawling',
        'icon' : 'bi bi-trash',
        'info_usuario': info_usuario,
        'singular' : 'sesión',
        'plural' : 'sesiones',
        # 'url_listar' : 'listar_',
        # 'url_crear' : 'crear_articulo',
        # 'url_ver' : 'ver_articulo',
        # 'url_editar' : 'modificar_articulo',
        # 'url_eliminar' : 'eliminar_articulo',
        'item': session,
    }
    return render(request, 'panel/generic_delete_object.html', context)


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler', 'viewer'])
def session_progress(request, pk):
    '''API endpoint para obtener progreso de una sesión (HTMX)'''

    session = get_object_or_404(CrawlSession, pk=pk)

    # Verificar permisos
    if not request.user.groups.filter(name='admin').exists() and session.user != request.user:
        return JsonResponse({'error': 'Sin permisos'}, status=403)

    # Obtener estadísticas actualizadas
    url_stats = {
        'pending': session.url_queue.filter(status='pending').count(),
        'processing': session.url_queue.filter(status='processing').count(),
        'completed': session.url_queue.filter(status='completed').count(),
        'failed': session.url_queue.filter(status='failed').count(),
        'skipped': session.url_queue.filter(status='skipped').count(),
    }

    progress_data = {
        'status': session.status,
        'status_display': session.get_status_display(),
        'progress_percentage': session.progress_percentage,
        'total_urls_discovered': session.total_urls_discovered,
        'total_urls_processed': session.total_urls_processed,
        'total_files_found': session.total_files_found,
        'total_errors': session.total_errors,
        'url_stats': url_stats,
        'is_active': session.is_active,
    }

    if request.headers.get('HX-Request'):
        # Respuesta para HTMX
        context = {
            'session': session,
            'progress_data': progress_data,
            'url_stats': url_stats,
        }
        return render(request, 'crawler/partials/progress_bar.html', context)
    else:
        # Respuesta JSON para API
        return JsonResponse(progress_data)


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler', 'viewer'])
def session_results(request, pk):
    '''Resultados de una sesión de crawling'''

    session = get_object_or_404(CrawlSession, pk=pk)

    # Verificar permisos
    if not request.user.groups.filter(name='admin').exists() and session.user != request.user:
        messages.error(request, 'No tienes permisos para ver los resultados de esta sesión.')
        return redirect('crawler:session_list')

    # Filtros
    file_type = request.GET.get('file_type', '')
    search = request.GET.get('search', '')

    results = session.results.all()

    if file_type:
        results = results.filter(url_queue_item__url_type=file_type)

    if search:
        results = results.filter(
            Q(file_name__icontains=search) |
            Q(url_queue_item__url__icontains=search) |
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )

    results = results.order_by('-created_at')

    # Paginación
    paginator = Paginator(results, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Tipos de archivo disponibles para filtrar
    available_file_types = session.results.values_list(
        'url_queue_item__url_type', flat=True
    ).distinct()

    info_user = info_header_user(request)

    context = {
        'page': f'Resultados: {session.name}',
        'icon': 'bi bi-files',
        'info_user': info_user,
        'session': session,
        'page_obj': page_obj,
        'available_file_types': available_file_types,
        'current_file_type': file_type,
        'current_search': search,
        'total_results': results.count(),
    }

    return render(request, 'crawler/session_results.html', context)


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler', 'viewer'])
def session_logs(request, pk):
    '''Logs de una sesión de crawling'''

    session = get_object_or_404(CrawlSession, pk=pk)

    # Verificar permisos
    if not request.user.groups.filter(name='admin').exists() and session.user != request.user:
        messages.error(request, 'No tienes permisos para ver los logs de esta sesión.')
        return redirect('crawler:session_list')

    # Filtros
    level = request.GET.get('level', '')
    search = request.GET.get('search', '')

    logs = session.logs.all()

    if level:
        logs = logs.filter(level=level)

    if search:
        logs = logs.filter(message__icontains=search)

    logs = logs.order_by('-created_at')

    # Paginación
    paginator = Paginator(logs, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Niveles disponibles para filtrar
    available_levels = session.logs.values_list('level', flat=True).distinct()

    info_user = info_header_user(request)

    context = {
        'page': f'Logs: {session.name}',
        'icon': 'bi bi-journal-text',
        'info_user': info_user,
        'session': session,
        'page_obj': page_obj,
        'available_levels': available_levels,
        'current_level': level,
        'current_search': search,
        'paginator': paginator,
        'page_number': page_number,
        'logs': logs,
        'total_logs': logs.count(),
    }

    return render(request, 'crawler/session_logs.html', context)


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler', 'viewer'])
def session_urls(request, pk):
    '''URLs descubiertas en una sesión de crawling'''
    session = get_object_or_404(CrawlSession, pk=pk)
    
    # Verificar permisos
    if not request.user.groups.filter(name='admin').exists() and session.user != request.user:
        messages.error(request, 'No tienes permisos para ver las URLs de esta sesión.')
        return redirect('crawler:session_list')
    
    # Filtros
    status = request.GET.get('status', '')
    url_type = request.GET.get('url_type', '')
    depth = request.GET.get('depth', '')
    search = request.GET.get('search', '')
    
    # Obtener URLs base
    urls = session.url_queue.all()
    
    # Aplicar filtros
    if status:
        urls = urls.filter(status=status)
    if url_type:
        urls = urls.filter(url_type=url_type)
    if depth:
        try:
            urls = urls.filter(depth=int(depth))
        except ValueError:
            pass
    if search:
        urls = urls.filter(url__icontains=search)
    
    # Ordenar por fecha de descubrimiento
    urls = urls.order_by('-discovered_at')
    
    # Calcular estadísticas de URLs
    url_stats = {
        'completed': session.url_queue.filter(status='completed').count(),
        'processing': session.url_queue.filter(status='processing').count(),
        'pending': session.url_queue.filter(status='pending').count(),
        'failed': session.url_queue.filter(status='failed').count(),
        'skipped': session.url_queue.filter(status='skipped').count(),
    }
    
    # Paginación
    paginator = Paginator(urls, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Opciones para filtros
    available_statuses = session.url_queue.values_list('status', flat=True).distinct()
    available_types = session.url_queue.values_list('url_type', flat=True).distinct()
    available_depths = session.url_queue.values_list('depth', flat=True).distinct().order_by('depth')
    
    info_user = info_header_user(request)
    
    context = {
        'page': f'URLs: {session.name}',
        'icon': 'bi bi-link-45deg',
        'info_user': info_user,
        'session': session,
        'urls': page_obj,  # URLs paginadas para la plantilla
        'page_obj': page_obj,  # Para compatibilidad con paginación
        'url_stats': url_stats,  # Estadísticas para las tarjetas
        'available_statuses': available_statuses,
        'available_types': available_types,
        'available_depths': available_depths,
        'current_status': status,
        'current_url_type': url_type,
        'current_depth': depth,
        'current_search': search,
        'total_urls': urls.count(),
    }
    
    return render(request, 'crawler/session_urls.html', context)


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler', 'viewer'])
def session_urls_old(request, pk):
    '''URLs descubiertas en una sesión de crawling'''

    session = get_object_or_404(CrawlSession, pk=pk)

    # Verificar permisos
    if not request.user.groups.filter(name='admin').exists() and session.user != request.user:
        messages.error(request, 'No tienes permisos para ver las URLs de esta sesión.')
        return redirect('crawler:session_list')

    # Filtros
    status = request.GET.get('status', '')
    url_type = request.GET.get('url_type', '')
    depth = request.GET.get('depth', '')
    search = request.GET.get('search', '')

    urls = session.url_queue.all()

    if status:
        urls = urls.filter(status=status)

    if url_type:
        urls = urls.filter(url_type=url_type)

    if depth:
        try:
            urls = urls.filter(depth=int(depth))
        except ValueError:
            pass

    if search:
        urls = urls.filter(url__icontains=search)

    urls = urls.order_by('-discovered_at')

    # Paginación
    paginator = Paginator(urls, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Opciones para filtros
    available_statuses = session.url_queue.values_list('status', flat=True).distinct()
    available_types = session.url_queue.values_list('url_type', flat=True).distinct()
    available_depths = session.url_queue.values_list('depth', flat=True).distinct().order_by('depth')

    info_user = info_header_user(request)

    context = {
        'page': f'URLs: {session.name}',
        'icon': 'bi bi-link-45deg',
        'info_user': info_user,
        'session': session,
        'page_obj': page_obj,
        'available_statuses': available_statuses,
        'available_types': available_types,
        'available_depths': available_depths,
        'current_status': status,
        'current_url_type': url_type,
        'current_depth': depth,
        'current_search': search,
        'total_urls': urls.count(),
    }

    return render(request, 'crawler/session_urls.html', context)


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler'])
@require_http_methods(["POST"])
def bulk_actions(request):
    '''Acciones en lote sobre sesiones'''

    form = BulkActionForm(request.POST)

    if not form.is_valid():
        messages.error(request, 'Datos del formulario inválidos.')
        return redirect('crawler:session_list')

    action = form.cleaned_data['action']
    session_ids = form.cleaned_data['session_ids']

    # Obtener sesiones y verificar permisos
    if request.user.groups.filter(name='admin').exists():
        sessions = CrawlSession.objects.filter(id__in=session_ids)
    else:
        sessions = CrawlSession.objects.filter(id__in=session_ids, user=request.user)

    if not sessions.exists():
        messages.error(request, 'No se encontraron sesiones válidas.')
        return redirect('crawler:session_list')

    # Ejecutar acción
    success_count = 0

    try:
        if action == 'pause':
            for session in sessions.filter(status='running'):
                session.status = 'paused'
                session.save()
                success_count += 1

        elif action == 'resume':
            for session in sessions.filter(status='paused'):
                start_crawl_session.delay(session.id)
                success_count += 1

        elif action == 'cancel':
            for session in sessions.filter(status__in=['pending', 'running', 'paused']):
                stop_crawl_session.delay(session.id)
                success_count += 1

        elif action == 'delete':
            sessions_to_delete = sessions.exclude(status__in=['running', 'processing'])
            success_count = sessions_to_delete.count()
            sessions_to_delete.delete()

        messages.success(request, f'Acción "{action}" aplicada a {success_count} sesiones.')

    except Exception as e:
        messages.error(request, f'Error ejecutando acción: {str(e)}')

    return redirect('crawler:session_list')


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler', 'viewer'])
def crawler_stats(request):
    '''Estadísticas generales del crawler'''

    # Filtrar por usuario si no es admin
    if request.user.groups.filter(name='admin').exists():
        sessions = CrawlSession.objects.all()
    else:
        sessions = CrawlSession.objects.filter(user=request.user)

    # Estadísticas generales
    stats = {
        'total_sessions': sessions.count(),
        'active_sessions': sessions.filter(status__in=['pending', 'running', 'paused']).count(),
        'completed_sessions': sessions.filter(status='completed').count(),
        'failed_sessions': sessions.filter(status='failed').count(),
        'total_urls_discovered': sum(s.total_urls_discovered for s in sessions),
        'total_urls_processed': sum(s.total_urls_processed for s in sessions),
        'total_files_found': sum(s.total_files_found for s in sessions),
        'total_errors': sum(s.total_errors for s in sessions),
    }

    # Estadísticas por estado
    status_stats = sessions.values('status').annotate(count=Count('id')).order_by('-count')

    # Dominios más crawleados
    domain_stats = sessions.values('target_domain').annotate(
        count=Count('id'),
        avg_files=Avg('total_files_found')
    ).order_by('-count')[:10]

    # Actividad por mes (últimos 12 meses)
    from django.db.models.functions import TruncMonth

    monthly_stats = sessions.filter(
        created_at__gte=timezone.now() - timezone.timedelta(days=365)
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id'),
        files_found=Count('results')
    ).order_by('month')

    # Top tipos de archivo encontrados
    file_type_stats = CrawlResult.objects.filter(
        session__in=sessions
    ).values('url_queue_item__url_type').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    info_user = info_header_user(request)

    context = {
        'page': 'Estadísticas del Crawler',
        'icon': 'bi bi-bar-chart-line',
        'info_user': info_user,
        'stats': stats,
        'status_stats': status_stats,
        'domain_stats': domain_stats,
        'monthly_stats': monthly_stats,
        'file_type_stats': file_type_stats,
    }

    return render(request, 'crawler/stats.html', context)


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler', 'viewer'])
def export_results(request, pk):
    '''Exportar resultados de crawling con opción de incluir metadatos'''
    
    session = get_object_or_404(CrawlSession, pk=pk)
    
    # Verificar acceso
    if session.user != request.user and not request.user.groups.filter(name='admin').exists():
        messages.error(request, 'No tienes permisos para exportar esta sesión.')
        return redirect('crawler:dashboard')
    
    # Parámetros de exportación
    export_format = request.GET.get('format', 'csv')
    include_metadata = request.GET.get('include_metadata', '0') == '1'
    include_analysis = request.GET.get('include_analysis', '0') == '1'
    report_type = request.GET.get('report_type', 'standard')
    
    try:
        if export_format == 'csv':
            return export_csv_with_metadata(session, include_metadata)
        elif export_format == 'json':
            return export_json_with_metadata(session, include_metadata, include_analysis)
        elif export_format == 'pdf':
            return export_pdf_report(session, report_type, include_metadata)
        else:
            messages.error(request, 'Formato de exportación no válido.')
            return redirect('crawler:session_detail', pk=pk)
            
    except Exception as e:
        logger.error(f"Error exportando resultados: {str(e)}")
        messages.error(request, f"Error exportando: {str(e)}")
        return redirect('crawler:session_detail', pk=pk)


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler', 'viewer'])
def export_results_old(request, pk):
    '''Exportar resultados de una sesión a CSV'''

    session = get_object_or_404(CrawlSession, pk=pk)

    # Verificar permisos
    if not request.user.groups.filter(name='admin').exists() and session.user != request.user:
        messages.error(request, 'No tienes permisos para exportar esta sesión.')
        return redirect('crawler:session_detail', pk=pk)

    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="crawl_results_{session.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    writer = csv.writer(response)

    # Headers
    writer.writerow([
        'URL', 'Tipo de Archivo', 'Nombre de Archivo', 'Tamaño (bytes)',
        'Código HTTP', 'Tiempo de Respuesta (s)', 'Profundidad',
        'URL Padre', 'Fecha Descubierta', 'Fecha Procesada', 'Estado'
    ])

    # Datos
    for url_item in session.url_queue.all():
        writer.writerow([
            url_item.url,
            url_item.url_type,
            getattr(url_item.results.first(), 'file_name', '') if url_item.results.exists() else '',
            url_item.file_size or '',
            url_item.http_status_code or '',
            url_item.response_time or '',
            url_item.depth,
            url_item.parent_url,
            url_item.discovered_at.strftime('%Y-%m-%d %H:%M:%S'),
            url_item.processed_at.strftime('%Y-%m-%d %H:%M:%S') if url_item.processed_at else '',
            url_item.get_status_display()
        ])

    return response


# API Views para integración con JavaScript/HTMX

@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler', 'viewer'])
def api_session_status(request, pk):
    '''API para obtener estado actual de una sesión'''

    session = get_object_or_404(CrawlSession, pk=pk)

    # Verificar permisos
    if not request.user.groups.filter(name='admin').exists() and session.user != request.user:
        return JsonResponse({'error': 'Sin permisos'}, status=403)

    data = {
        'id': session.id,
        'status': session.status,
        'status_display': session.get_status_display(),
        'progress_percentage': session.progress_percentage,
        'total_urls_discovered': session.total_urls_discovered,
        'total_urls_processed': session.total_urls_processed,
        'total_files_found': session.total_files_found,
        'total_errors': session.total_errors,
        'is_active': session.is_active,
        'started_at': session.started_at.isoformat() if session.started_at else None,
        'completed_at': session.completed_at.isoformat() if session.completed_at else None,
    }

    return JsonResponse(data)


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler', 'viewer'])
def api_dashboard_stats(request):
    '''API para estadísticas del dashboard'''

    if request.user.groups.filter(name='admin').exists():
        sessions = CrawlSession.objects.all()
    else:
        sessions = CrawlSession.objects.filter(user=request.user)

    data = {
        'total_sessions': sessions.count(),
        'active_sessions': sessions.filter(status__in=['pending', 'running', 'paused']).count(),
        'completed_sessions': sessions.filter(status='completed').count(),
        'failed_sessions': sessions.filter(status='failed').count(),
        'total_files_found': sum(s.total_files_found for s in sessions),
    }

    return JsonResponse(data)


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler', 'viewer'])
def file_metadata_detail(request, result_id):
    '''Vista detallada de metadatos de un archivo específico'''
    
    result = get_object_or_404(CrawlResult, id=result_id)
    
    # Verificar que el usuario tenga acceso a esta sesión
    if result.session.user != request.user and not request.user.groups.filter(name='admin').exists():
        messages.error(request, 'No tienes permisos para ver este archivo.')
        return redirect('crawler:dashboard')
    
    # Organizar metadatos por categorías
    metadata_categories = {}
    
    if result.metadata:
        for key, value in result.metadata.items():
            if key.endswith('_metadata'):
                # Es una categoría de metadatos (pdf_metadata, office_metadata, etc.)
                category_name = key.replace('_metadata', '').title()
                metadata_categories[category_name] = value
            elif key in ['file_path', 'file_url', 'referrer', 'file_size', 'file_hash_sha256']:
                # Información básica del archivo
                if 'Información Básica' not in metadata_categories:
                    metadata_categories['Información Básica'] = {}
                metadata_categories['Información Básica'][key] = value
            else:
                # Otros metadatos
                if 'Otros' not in metadata_categories:
                    metadata_categories['Otros'] = {}
                metadata_categories['Otros'][key] = value
    
    info_user = info_header_user(request)
    
    context = {
        'page': f'Metadatos - {result.file_name}',
        'icon': 'bi bi-file-earmark-text',
        'info_user': info_user,
        'result': result,
        'metadata_categories': metadata_categories,
        'session': result.session,
    }
    
    return render(request, 'crawler/file_metadata_detail.html', context)



@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler', 'viewer'])
def session_metadata_summary(request, pk):
    '''Vista resumen de metadatos de una sesión'''
    
    session = get_object_or_404(CrawlSession, pk=pk)
    
    # Verificar acceso
    if session.user != request.user and not request.user.groups.filter(name='admin').exists():
        messages.error(request, 'No tienes permisos para ver esta sesión.')
        return redirect('crawler:dashboard')
    
    # Estadísticas de metadatos
    results_with_metadata = CrawlResult.objects.filter(
        session=session
    ).exclude(metadata={})
    
    # Contar tipos de archivo
    file_types_stats = {}
    authors_found = set()
    software_found = set()
    dates_found = []
    
    for result in results_with_metadata:
        # Tipo de archivo
        file_ext = os.path.splitext(result.file_name)[1].lower()
        file_types_stats[file_ext] = file_types_stats.get(file_ext, 0) + 1
        
        # Extraer información interesante
        metadata = result.metadata
        
        # Autores
        for category in ['pdf_metadata', 'office_metadata']:
            if category in metadata:
                if 'author' in metadata[category]:
                    authors_found.add(metadata[category]['author'])
                if 'creator' in metadata[category]:
                    authors_found.add(metadata[category]['creator'])
        
        # Software
        for category in ['pdf_metadata', 'office_metadata', 'exif_metadata']:
            if category in metadata:
                if 'producer' in metadata[category]:
                    software_found.add(metadata[category]['producer'])
                if 'software' in metadata[category]:
                    software_found.add(metadata[category]['software'])
                if 'creator' in metadata[category] and 'Microsoft' in str(metadata[category]['creator']):
                    software_found.add(metadata[category]['creator'])
        
        # Fechas de creación
        for category in ['pdf_metadata', 'office_metadata']:
            if category in metadata:
                if 'creation_date' in metadata[category]:
                    dates_found.append(metadata[category]['creation_date'])
                if 'created' in metadata[category]:
                    dates_found.append(metadata[category]['created'])
    
    # Top 10 más frecuentes
    top_authors = sorted(list(authors_found))[:10]
    top_software = sorted(list(software_found))[:10]
    
    stats = {
        'total_files_with_metadata': results_with_metadata.count(),
        'file_types_distribution': file_types_stats,
        'unique_authors_count': len(authors_found),
        'unique_software_count': len(software_found),
        'top_authors': top_authors,
        'top_software': top_software,
    }
    
    info_user = info_header_user(request)
    
    context = {
        'page': f'Resumen Metadatos - {session.name}',
        'icon': 'bi bi-graph-up',
        'info_user': info_user,
        'session': session,
        'stats': stats,
        'results_with_metadata': results_with_metadata[:20],  # Mostrar solo los primeros 20
    }
    
    return render(request, 'crawler/session_metadata_summary.html', context)



@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler', 'viewer'])
def session_advanced_analysis(request, pk):
    '''Vista de análisis avanzado de metadatos con evaluación de riesgos'''
    
    session = get_object_or_404(CrawlSession, pk=pk)
    
    # Verificar acceso
    if session.user != request.user and not request.user.groups.filter(name='admin').exists():
        messages.error(request, 'No tienes permisos para ver esta sesión.')
        return redirect('crawler:dashboard')
    
    try:
        # Importar y ejecutar análisis
        from .metadata_utils import analyze_session_metadata
        analysis = analyze_session_metadata(session)
        
        if 'error' in analysis:
            messages.warning(request, analysis['error'])
            return redirect('crawler:session_detail', pk=pk)
        
        # Preparar datos para gráficos
        chart_data = prepare_chart_data(analysis)
        
    except Exception as e:
        logger.error(f"Error ejecutando análisis avanzado: {str(e)}")
        messages.error(request, f"Error ejecutando análisis: {str(e)}")
        return redirect('crawler:session_detail', pk=pk)
    
    info_user = info_header_user(request)
    
    context = {
        'page': f'Análisis Avanzado - {session.name}',
        'icon': 'bi bi-graph-up-arrow',
        'info_user': info_user,
        'session': session,
        'analysis': analysis,
        'chart_data': chart_data,
    }
    
    return render(request, 'crawler/session_advanced_analysis.html', context)


def prepare_chart_data(analysis):
    '''Prepara datos para visualizaciones interactivas'''
    chart_data = {}
    
    # Datos para gráfico de software
    software_analysis = analysis.get('software_analysis', {})
    if 'most_common_software' in software_analysis:
        software_labels = [item[0][:30] for item in software_analysis['most_common_software'][:10]]
        software_counts = [item[1] for item in software_analysis['most_common_software'][:10]]
        
        chart_data['software_chart'] = {
            'labels': software_labels,
            'data': software_counts,
            'backgroundColor': [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF',
                '#4BC0C0', '#FF6384'
            ]
        }
    
    # Datos para gráfico temporal
    temporal_analysis = analysis.get('temporal_analysis', {})
    if 'activity_by_month' in temporal_analysis:
        months = sorted(temporal_analysis['activity_by_month'].keys())
        activity_counts = [temporal_analysis['activity_by_month'][month] for month in months]
        
        chart_data['temporal_chart'] = {
            'labels': months,
            'data': activity_counts,
            'borderColor': '#36A2EB',
            'backgroundColor': 'rgba(54, 162, 235, 0.2)'
        }
    
    # Datos para gráfico de riesgos
    security_risks = analysis.get('risk_assessment', {})
    privacy_risks = analysis.get('privacy_assessment', {})
    
    chart_data['risk_chart'] = {
        'labels': ['Seguridad', 'Privacidad'],
        'data': [
            security_risks.get('overall_risk_score', 0),
            privacy_risks.get('overall_privacy_score', 0)
        ],
        'backgroundColor': ['#FF6384', '#FF9F40'],
        'borderColor': ['#FF6384', '#FF9F40']
    }
    
    return chart_data


def export_csv_with_metadata(session, include_metadata=False):
    '''Exporta resultados a CSV con opción de incluir metadatos'''
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="crawl_results_{session.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Headers básicos
    headers = [
        'URL', 'Referrer', 'Tipo_Archivo', 'Tamaño_Bytes', 'Estado_HTTP',
        'Tiempo_Respuesta', 'Descubierto_En', 'Procesado_En', 'Profundidad'
    ]
    
    # Headers adicionales si se incluyen metadatos
    if include_metadata:
        headers.extend([
            'Tiene_Metadatos', 'Autor', 'Creador', 'Fecha_Creacion', 
            'Fecha_Modificacion', 'Software_Usado', 'Titulo', 'Coordenadas_GPS',
            'Hash_Archivo', 'Metadatos_JSON'
        ])
    
    writer.writerow(headers)
    
    # Obtener resultados
    url_items = URLQueue.objects.filter(session=session).select_related().order_by('discovered_at')
    
    for url_item in url_items:
        row = [
            url_item.url,
            url_item.referrer or '',
            url_item.url_type or '',
            url_item.file_size or 0,
            url_item.http_status_code or '',
            url_item.response_time or 0,
            url_item.discovered_at.isoformat() if url_item.discovered_at else '',
            url_item.processed_at.isoformat() if url_item.processed_at else '',
            url_item.depth
        ]
        
        if include_metadata:
            # Buscar resultado asociado con metadatos
            try:
                result = CrawlResult.objects.get(url_queue_item=url_item)
                metadata = result.metadata or {}
                
                # Extraer campos específicos de metadatos
                author = ''
                creator = ''
                creation_date = ''
                modification_date = ''
                software = ''
                title = result.title or ''
                gps_coords = ''
                file_hash = result.file_hash or ''
                
                # Buscar en diferentes categorías de metadatos
                for category in ['pdf_metadata', 'office_metadata', 'exif_metadata']:
                    if category in metadata:
                        cat_data = metadata[category]
                        
                        if not author and 'author' in cat_data:
                            author = str(cat_data['author'])
                        if not creator and 'creator' in cat_data:
                            creator = str(cat_data['creator'])
                        if not creation_date and 'creation_date' in cat_data:
                            creation_date = str(cat_data['creation_date'])
                        elif not creation_date and 'created' in cat_data:
                            creation_date = str(cat_data['created'])
                        if not modification_date and 'modification_date' in cat_data:
                            modification_date = str(cat_data['modification_date'])
                        elif not modification_date and 'modified' in cat_data:
                            modification_date = str(cat_data['modified'])
                        if not software and 'producer' in cat_data:
                            software = str(cat_data['producer'])
                        elif not software and 'software' in cat_data:
                            software = str(cat_data['software'])
                        
                        # GPS específico para EXIF
                        if category == 'exif_metadata' and 'gps_coordinates' in cat_data:
                            gps_data = cat_data['gps_coordinates']
                            if isinstance(gps_data, dict) and 'coordinates_string' in gps_data:
                                gps_coords = gps_data['coordinates_string']
                
                row.extend([
                    'Sí' if metadata else 'No',
                    author,
                    creator,
                    creation_date,
                    modification_date,
                    software,
                    title,
                    gps_coords,
                    file_hash,
                    json.dumps(metadata, ensure_ascii=False) if metadata else ''
                ])
                
            except CrawlResult.DoesNotExist:
                row.extend(['No', '', '', '', '', '', '', '', '', ''])
        
        writer.writerow(row)
    
    return response


def export_json_with_metadata(session, include_metadata=False, include_analysis=False):
    '''Exporta resultados a JSON con metadatos y análisis'''
    from django.http import JsonResponse
    import json
    
    data = {
        'session_info': {
            'id': session.id,
            'name': session.name,
            'target_domain': session.target_domain,
            'target_url': session.target_url,
            'status': session.status,
            'created_at': session.created_at.isoformat(),
            'started_at': session.started_at.isoformat() if session.started_at else None,
            'completed_at': session.completed_at.isoformat() if session.completed_at else None,
            'total_urls_processed': session.total_urls_processed,
            'total_files_found': session.total_files_found,
        },
        'urls_discovered': []
    }
    
    # URLs descubiertas
    url_items = URLQueue.objects.filter(session=session).select_related()
    
    for url_item in url_items:
        url_data = {
            'url': url_item.url,
            'referrer': url_item.referrer,
            'parent_url': url_item.parent_url,
            'depth': url_item.depth,
            'url_type': url_item.url_type,
            'file_size': url_item.file_size,
            'content_type': url_item.content_type,
            'status': url_item.status,
            'http_status_code': url_item.http_status_code,
            'response_time': url_item.response_time,
            'discovered_at': url_item.discovered_at.isoformat() if url_item.discovered_at else None,
            'processed_at': url_item.processed_at.isoformat() if url_item.processed_at else None,
            'has_metadata': url_item.has_metadata,
        }
        
        # Incluir metadatos si se solicita
        if include_metadata:
            try:
                result = CrawlResult.objects.get(url_queue_item=url_item)
                url_data['metadata'] = result.metadata
                url_data['file_hash'] = result.file_hash
                url_data['file_path'] = result.file_path
                url_data['title'] = result.title
                url_data['description'] = result.description
                url_data['keywords'] = result.keywords
            except CrawlResult.DoesNotExist:
                url_data['metadata'] = None
        
        data['urls_discovered'].append(url_data)
    
    # Incluir análisis avanzado si se solicita
    if include_analysis:
        try:
            from .metadata_utils import analyze_session_metadata
            analysis = analyze_session_metadata(session)
            data['advanced_analysis'] = analysis
        except Exception as e:
            data['analysis_error'] = str(e)
    
    # Crear respuesta JSON
    response = JsonResponse(data, json_dumps_params={'ensure_ascii': False, 'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="crawl_export_{session.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
    
    return response


def export_pdf_report(session, report_type='standard', include_metadata=False):
    '''Genera reporte PDF con metadatos'''
    from django.http import HttpResponse
    from django.template.loader import get_template
    
    try:
        # Intentar importar librería PDF
        from xhtml2pdf import pisa
        pdf_available = True
    except ImportError:
        pdf_available = False
    
    if not pdf_available:
        messages.error(request, 'Librería PDF no disponible. Instalar con: pip install xhtml2pdf')
        return redirect('crawler:session_detail', pk=session.pk)
    
    # Preparar datos según tipo de reporte
    context = {
        'session': session,
        'generated_at': timezone.now(),
        'include_metadata': include_metadata,
    }
    
    if report_type == 'security':
        # Reporte de seguridad con análisis de riesgos
        try:
            from .metadata_utils import analyze_session_metadata
            analysis = analyze_session_metadata(session)
            context['analysis'] = analysis
            template_name = 'crawler/reports/security_report.html'
        except Exception as e:
            context['analysis_error'] = str(e)
            template_name = 'crawler/reports/basic_report.html'
    else:
        # Reporte estándar
        results = CrawlResult.objects.filter(session=session).select_related('url_queue_item')
        context['results'] = results
        template_name = 'crawler/reports/standard_report.html'
    
    # Generar PDF
    template = get_template(template_name)
    html = template.render(context)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="crawl_report_{session.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Error generando PDF', status=500)
    
    return response