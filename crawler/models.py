from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
import json

class CrawlSession(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('running', 'Ejecutándose'),
        ('paused', 'Pausado'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
        ('cancelled', 'Cancelado'),
    ]

    PRIORITY_CHOICES = [
        (1, 'Muy Alta'),
        (2, 'Alta'),
        (3, 'Normal'),
        (4, 'Baja'),
        (5, 'Muy Baja'),
    ]

    # Información básica
    name = models.CharField(max_length=255, help_text="Nombre descriptivo para esta sesión")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='crawl_sessions')
    target_domain = models.CharField(max_length=255, help_text="Dominio objetivo (ej: example.com)")
    target_url = models.URLField(help_text="URL inicial para comenzar el crawling")

    # Configuración de crawling
    max_depth = models.IntegerField(default=3, help_text="Profundidad máxima de crawling")
    rate_limit = models.FloatField(default=1.0, help_text="Requests por segundo")
    max_pages = models.IntegerField(default=1000, help_text="Máximo número de páginas a crawlear")
    max_file_size = models.IntegerField(default=52428800, help_text="Tamaño máximo de archivo en bytes (50MB)")

    # Tipos de archivo a buscar
    file_types = models.JSONField(
        default=list,
        help_text="Lista de extensiones de archivo a buscar",
        blank=True
    )

    # Configuración avanzada
    respect_robots_txt = models.BooleanField(default=True, help_text="Respetar robots.txt")
    follow_redirects = models.BooleanField(default=True, help_text="Seguir redirecciones")
    extract_metadata = models.BooleanField(default=True, help_text="Extraer metadatos de archivos encontrados")

    # Estados y estadísticas
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=3)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Estadísticas
    total_urls_discovered = models.IntegerField(default=0)
    total_urls_processed = models.IntegerField(default=0)
    total_files_found = models.IntegerField(default=0)
    total_errors = models.IntegerField(default=0)

    # Configuración adicional como JSON
    advanced_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Configuración avanzada adicional"
    )

    class Meta:
        verbose_name = 'Sesión de Crawling'
        verbose_name_plural = 'Sesiones de Crawling'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.target_domain}"

    def get_absolute_url(self):
        return reverse('crawler:session_detail', kwargs={'pk': self.pk})

    @property
    def progress_percentage(self):
        if self.max_pages == 0:
            return 0
        return min(100, (self.total_urls_processed / self.max_pages) * 100)

    @property
    def is_active(self):
        return self.status in ['pending', 'running', 'paused']

    def get_file_types_list(self):
        '''Retorna la lista de tipos de archivo como lista Python'''
        if isinstance(self.file_types, str):
            try:
                return json.loads(self.file_types)
            except json.JSONDecodeError:
                return []
        return self.file_types or []

    def set_file_types_list(self, file_types_list):
        '''Establece la lista de tipos de archivo'''
        self.file_types = file_types_list


class URLQueue(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
        ('skipped', 'Omitido'),
    ]

    URL_TYPE_CHOICES = [
        ('html', 'HTML'),
        ('pdf', 'PDF'),
        ('doc', 'Documento Word'),
        ('docx', 'Documento Word XML'),
        ('xls', 'Excel'),
        ('xlsx', 'Excel XML'),
        ('ppt', 'PowerPoint'),
        ('pptx', 'PowerPoint XML'),
        ('jpg', 'JPEG'),
        ('jpeg', 'JPEG'),
        ('png', 'PNG'),
        ('gif', 'GIF'),
        ('tiff', 'TIFF'),
        ('mp3', 'MP3'),
        ('mp4', 'MP4'),
        ('xml', 'XML'),
        ('json', 'JSON'),
        ('other', 'Otro'),
    ]

    session = models.ForeignKey(CrawlSession, on_delete=models.CASCADE, related_name='url_queue')
    url = models.URLField(max_length=2048)
    parent_url = models.URLField(max_length=2048, blank=True, help_text="URL desde donde se descubrió esta URL")

    # Información de crawling
    depth = models.IntegerField(default=0, help_text="Profundidad desde la URL inicial")
    url_type = models.CharField(max_length=10, choices=URL_TYPE_CHOICES, default='html')
    file_size = models.IntegerField(null=True, blank=True, help_text="Tamaño del archivo en bytes")
    content_type = models.CharField(max_length=100, blank=True, help_text="Content-Type del response")

    # Estado y procesamiento
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.IntegerField(default=5, help_text="Prioridad (1=más alta, 5=más baja)")
    retry_count = models.IntegerField(default=0)

    # Timestamps
    discovered_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    # Resultados del procesamiento
    http_status_code = models.IntegerField(null=True, blank=True)
    response_time = models.FloatField(null=True, blank=True, help_text="Tiempo de respuesta en segundos")
    error_message = models.TextField(blank=True)

    # Metadatos extraídos
    has_metadata = models.BooleanField(default=False)
    metadata_extracted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'URL en Cola'
        verbose_name_plural = 'URLs en Cola'
        ordering = ['priority', 'discovered_at']
        unique_together = ['session', 'url']

    def __str__(self):
        return f"{self.url} (depth: {self.depth})"


class CrawlResult(models.Model):
    '''Almacena los resultados y archivos encontrados durante el crawling'''

    session = models.ForeignKey(CrawlSession, on_delete=models.CASCADE, related_name='results')
    url_queue_item = models.ForeignKey(URLQueue, on_delete=models.CASCADE, related_name='results')

    # Información del archivo/recurso
    file_name = models.CharField(max_length=255, blank=True)
    file_path = models.CharField(max_length=500, blank=True, help_text="Ruta local donde se guardó el archivo")
    file_hash = models.CharField(max_length=64, blank=True, help_text="Hash SHA-256 del archivo")

    # Metadatos extraídos (como JSON)
    metadata = models.JSONField(default=dict, blank=True)

    # Información adicional
    title = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    keywords = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Resultado de Crawling'
        verbose_name_plural = 'Resultados de Crawling'
        ordering = ['-created_at']

    def __str__(self):
        return f"Resultado: {self.url_queue_item.url}"


class CrawlLog(models.Model):
    '''Log de eventos durante el crawling'''

    LOG_LEVEL_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]

    session = models.ForeignKey(CrawlSession, on_delete=models.CASCADE, related_name='logs')
    level = models.CharField(max_length=10, choices=LOG_LEVEL_CHOICES)
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Log de Crawling'
        verbose_name_plural = 'Logs de Crawling'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.level}] {self.message[:50]}..."
