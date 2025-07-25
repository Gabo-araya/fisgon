from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
import os
import logging

from .models import CrawlSession, CrawlResult, URLQueue

logger = logging.getLogger('crawler')


@receiver(post_save, sender=CrawlSession)
def crawl_session_created(sender, instance, created, **kwargs):
    """
    Se ejecuta cuando se crea o actualiza una sesión de crawling
    """
    if created:
        logger.info(f'Nueva sesión de crawling creada: {instance.name} por {instance.user.username}')

        # Crear directorio para almacenar archivos de esta sesión
        from django.conf import settings
        session_dir = os.path.join(settings.MEDIA_ROOT, 'crawler', str(instance.id))
        os.makedirs(session_dir, exist_ok=True)


@receiver(post_save, sender=URLQueue)
def url_queue_updated(sender, instance, created, **kwargs):
    """
    Se ejecuta cuando se actualiza el estado de una URL en la cola
    """
    if not created and instance.status == 'completed':
        # Actualizar estadísticas de la sesión
        session = instance.session
        session.total_urls_processed = session.url_queue.filter(status='completed').count()
        session.total_files_found = session.results.count()
        session.total_errors = session.url_queue.filter(status='failed').count()
        session.save(update_fields=['total_urls_processed', 'total_files_found', 'total_errors'])


@receiver(pre_delete, sender=CrawlSession)
def cleanup_session_files(sender, instance, **kwargs):
    """
    Limpia archivos cuando se elimina una sesión
    """
    try:
        from django.conf import settings
        import shutil

        session_dir = os.path.join(settings.MEDIA_ROOT, 'crawler', str(instance.id))
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
            logger.info(f'Archivos de sesión {instance.id} eliminados')
    except Exception as e:
        logger.error(f'Error eliminando archivos de sesión {instance.id}: {str(e)}')


@receiver(pre_delete, sender=CrawlResult)
def cleanup_result_file(sender, instance, **kwargs):
    """
    Elimina archivo físico cuando se borra un resultado
    """
    try:
        if instance.file_path and os.path.exists(instance.file_path):
            os.remove(instance.file_path)
            logger.info(f'Archivo eliminado: {instance.file_path}')
    except Exception as e:
        logger.error(f'Error eliminando archivo {instance.file_path}: {str(e)}')
