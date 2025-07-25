from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import CrawlSession, URLQueue, CrawlResult, CrawlLog


@admin.register(CrawlSession)
class CrawlSessionAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'user', 'target_domain', 'status', 'progress_display',
        'total_files_found', 'created_at', 'action_links'
    ]
    list_filter = ['status', 'created_at', 'user', 'respect_robots_txt']
    search_fields = ['name', 'target_domain', 'target_url', 'user__username']
    readonly_fields = [
        'created_at', 'started_at', 'completed_at', 'updated_at',
        'total_urls_discovered', 'total_urls_processed', 'total_files_found', 'total_errors'
    ]

    # fieldsets = (
    #     ('Información Básica', {
    #         'fields': ('name', 'user', 'target_url', 'target_domain')
    #     }),
    #     ('Configuración', {
    #         'fields': ('max_depth', 'rate_limit', 'max_pages', 'max_file_size', 'file_types')
    #     }),
    #     ('Opciones', {
    #         'fields': ('respect_robots_txt', 'follow_redirects', 'extract_metadata', 'priority')
    #     }),
    #     ('Estado', {
    #         'fields': ('status', 'created_at', 'started_at', 'completed_at', 'updated_at')
    #     }),
    #     ('Estadísticas', {
    #         'fields': ('total_urls_discovered', 'total_urls_processed', 'total_files_found', 'total_errors')
    #     }),
    #     ('Configuración Avanzada', {
    #         'fields': ('advanced_config',),
    #         'classes': ('collapse',)
    #     })
    # )

    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'user', 'target_domain', 'target_url', 'status', 'priority')
        }),
        ('Configuración de Crawling', {
            'fields': ('max_depth', 'rate_limit', 'max_pages', 'max_file_size', 'file_types')
        }),
        ('Opciones Avanzadas', {
            'fields': ('respect_robots_txt', 'follow_redirects', 'extract_metadata', 'advanced_config')
        }),
        ('Estadísticas', {
            'fields': ('total_urls_discovered', 'total_urls_processed', 'total_files_found', 'total_errors'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


    # def progress_display(self, obj):
    #     if obj.max_pages > 0:
    #         percentage = (obj.total_urls_processed / obj.max_pages) * 100
    #         percentage = min(100, percentage)

    #         if obj.status == 'completed':
    #             color = 'success'
    #         elif obj.status == 'failed':
    #             color = 'danger'
    #         elif obj.status == 'running':
    #             color = 'primary'
    #         else:
    #             color = 'secondary'

    #         return format_html(
    #             '<div class="progress" style="width: 100px; height: 20px;">'
    #             '<div class="progress-bar bg-{}" style="width: {}%">{:.1f}%</div>'
    #             '</div>',
    #             color, percentage, percentage
    #         )
    #     return '-'
    # progress_display.short_description = 'Progreso'

    def progress_display(self, obj):
        percentage = obj.progress_percentage
        if percentage > 0:
            if percentage < 30:
                color = 'danger'
            elif percentage < 70:
                color = 'warning'
            else:
                color = 'success'

            return mark_safe(
                '<div class="progress" style="width: 100px;">'
                '<div class="progress-bar bg-{}" style="width: {}%">{:.1f}%</div>'
                '</div>'.format(color, percentage, percentage)
            )
        return '-'
    progress_display.short_description = 'Progreso'



    def action_links(self, obj):
        links = []

        # Link al detalle en la aplicación
        detail_url = reverse('crawler:session_detail', args=[obj.pk])
        links.append(f'<a href="{detail_url}" target="_blank">Ver Detalle</a>')

        # Link a resultados si existen
        if obj.total_files_found > 0:
            results_url = reverse('crawler:session_results', args=[obj.pk])
            links.append(f'<a href="{results_url}" target="_blank">Resultados</a>')

        return mark_safe(' | '.join(links))
    action_links.short_description = 'Acciones'

    actions = ['mark_as_cancelled']

    def mark_as_cancelled(self, request, queryset):
        updated = queryset.filter(status__in=['pending', 'running', 'paused']).update(status='cancelled')
        self.message_user(request, f'{updated} sesiones marcadas como canceladas.')
    mark_as_cancelled.short_description = 'Marcar como canceladas'



@admin.register(URLQueue)
class URLQueueAdmin(admin.ModelAdmin):
    list_display = [
        'url_short', 'session_name', 'url_type', 'status', 'depth',
        'http_status_code', 'response_time', 'discovered_at'
    ]
    list_filter = ['status', 'url_type', 'depth', 'session__status', 'discovered_at']
    search_fields = ['url', 'session__name', 'parent_url']
    readonly_fields = ['discovered_at', 'processed_at']
    raw_id_fields = ['session']

    def url_short(self, obj):
        if len(obj.url) > 60:
            return obj.url[:60] + '...'
        return obj.url
    url_short.short_description = 'URL'

    def session_name(self, obj):
        return obj.session.name
    session_name.short_description = 'Sesión'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('session')



@admin.register(CrawlResult)
class CrawlResultAdmin(admin.ModelAdmin):
    list_display = [
        'file_name', 'session_name', 'url_short', 'file_size_display',
        'has_metadata_display', 'created_at'
    ]
    # list_filter = ['created_at', 'url_queue_item__url_type', 'url_queue_item__session__status']
    # search_fields = ['file_name', 'title', 'description', 'url_queue_item__url']
    search_fields = ['file_name', 'url_queue_item__url', 'url_queue_item__session__name']
    # readonly_fields = ['created_at', 'updated_at', 'file_hash']
    # raw_id_fields = ['session', 'url_queue_item']

    def session_name(self, obj):
        return obj.session.name
    session_name.short_description = 'Sesión'

    def url_short(self, obj):
        url = obj.url_queue_item.url
        if len(url) > 50:
            return url[:50] + '...'
        return url
    url_short.short_description = 'URL'


    # def file_size_display(self, obj):
    #     if obj.url_queue_item.file_size:
    #         size_bytes = obj.url_queue_item.file_size
    #         if size_bytes < 1024:
    #             return f'{size_bytes} B'
    #         elif size_bytes < 1024 * 1024:
    #             return f'{size_bytes / 1024:.1f} KB'
    #         else:
    #             return f'{size_bytes / (1024 * 1024):.1f} MB'
    #     return '-'
    # file_size_display.short_description = 'Tamaño'

    def file_size_display(self, obj):
        if obj.url_queue_item.file_size:
            size = obj.url_queue_item.file_size
            if size > 1024*1024:
                return f"{size/(1024*1024):.1f} MB"
            elif size > 1024:
                return f"{size/1024:.1f} KB"
            else:
                return f"{size} B"
        return '-'
    file_size_display.short_description = 'Tamaño'


    # def has_metadata_display(self, obj):
    #     if obj.metadata:
    #         return format_html(
    #             '<span style="color: green;">✓ Sí ({} campos)</span>',
    #             len(obj.metadata)
    #         )
    #     return format_html('<span style="color: red;">✗ No</span>')
    # has_metadata_display.short_description = 'Metadatos'

    def has_metadata_display(self, obj):
        if obj.metadata:
            return mark_safe('<span style="color: green;">✓</span>')
        return mark_safe('<span style="color: red;">✗</span>')
    has_metadata_display.short_description = 'Metadatos'


    # def get_queryset(self, request):
    #     return super().get_queryset(request).select_related('session', 'url_queue_item')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'url_queue_item__session'
        )



@admin.register(CrawlLog)
class CrawlLogAdmin(admin.ModelAdmin):
    list_display = ['session_name', 'level', 'message_short', 'created_at']
    list_filter = ['level', 'created_at', 'session__status']
    search_fields = ['message', 'session__name']
    readonly_fields = ['created_at']
    raw_id_fields = ['session']

    def session_name(self, obj):
        return obj.session.name
    session_name.short_description = 'Sesión'

    def message_short(self, obj):
        if len(obj.message) > 80:
            return obj.message[:80] + '...'
        return obj.message
    message_short.short_description = 'Mensaje'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('session')

    # Configuración para mostrar logs más recientes primero
    ordering = ['-created_at']


# Personalización del admin site
admin.site.site_header = "FISGÓN - Administración del Sistema Crawler"
admin.site.site_title = "FISGÓN Admin"
admin.site.index_title = "Panel de Administración"
