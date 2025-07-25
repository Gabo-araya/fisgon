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
@allowed_users(allowed_roles=['admin', 'crawler'])
def crawler_dashboard(request):
    """Dashboard principal del crawler"""

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
    """Crear nueva sesión de crawling"""

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
@allowed_users(allowed_roles=['admin', 'crawler', 'viewer'])
def session_list(request):
    """Lista de sesiones de crawling"""

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
    """Detalle de una sesión de crawling"""

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
    """Iniciar una sesión de crawling"""

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
    """Detener una sesión de crawling"""

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
@require_http_methods(["POST"])
def delete_session(request, pk):
    """Eliminar una sesión de crawling"""

    session = get_object_or_404(CrawlSession, pk=pk)

    # Verificar permisos
    if not request.user.groups.filter(name='admin').exists() and session.user != request.user:
        messages.error(request, 'No tienes permisos para eliminar esta sesión.')
        return redirect('crawler:session_detail', pk=pk)

    if session.status in ['running', 'processing']:
        messages.error(request, 'No se puede eliminar una sesión en ejecución. Detén la sesión primero.')
        return redirect('crawler:session_detail', pk=pk)

    session_name = session.name
    session.delete()

    messages.success(request, f'Sesión "{session_name}" eliminada exitosamente.')
    return redirect('crawler:session_list')


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler', 'viewer'])
def session_progress(request, pk):
    """API endpoint para obtener progreso de una sesión (HTMX)"""

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
    """Resultados de una sesión de crawling"""

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
    """Logs de una sesión de crawling"""

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
        'total_logs': logs.count(),
    }

    return render(request, 'crawler/session_logs.html', context)


@login_required(login_url='entrar')
@allowed_users(allowed_roles=['admin', 'crawler', 'viewer'])
def session_urls(request, pk):
    """URLs descubiertas en una sesión de crawling"""

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
    """Acciones en lote sobre sesiones"""

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
    """Estadísticas generales del crawler"""

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
    from django.db.models import TruncMonth
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
    """Exportar resultados de una sesión a CSV"""

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
    """API para obtener estado actual de una sesión"""

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
    """API para estadísticas del dashboard"""

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
        '
