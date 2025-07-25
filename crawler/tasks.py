from celery import shared_task, current_task
from django.utils import timezone
from django.conf import settings
import requests
import time
import logging
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
import hashlib
import os
from typing import List, Dict, Set

from .models import CrawlSession, URLQueue, CrawlResult, CrawlLog
from .utils import (
    is_valid_url,
    get_file_extension,
    is_allowed_file_type,
    extract_robots_txt,
    should_respect_robots_txt
)

logger = logging.getLogger('crawler')

@shared_task(bind=True)
def start_crawl_session(self, session_id: int):
    """Tarea principal que inicia una sesión de crawling"""
    try:
        session = CrawlSession.objects.get(id=session_id)
        session.status = 'running'
        session.started_at = timezone.now()
        session.save()

        # Log de inicio
        CrawlLog.objects.create(
            session=session,
            level='INFO',
            message=f'Iniciando crawling de {session.target_domain}',
            details={'target_url': session.target_url}
        )

        # Agregar URL inicial a la cola
        URLQueue.objects.get_or_create(
            session=session,
            url=session.target_url,
            defaults={
                'depth': 0,
                'url_type': 'html',
                'priority': 1,
                'status': 'pending'
            }
        )

        # Procesar robots.txt si está habilitado
        if session.respect_robots_txt:
            process_robots_txt.delay(session_id)

        # Iniciar procesamiento de URLs
        process_url_queue.delay(session_id)

        return {'status': 'started', 'session_id': session_id}

    except CrawlSession.DoesNotExist:
        logger.error(f'Sesión {session_id} no encontrada')
        return {'status': 'error', 'message': 'Sesión no encontrada'}
    except Exception as e:
        logger.error(f'Error iniciando crawling: {str(e)}')
        if 'session' in locals():
            session.status = 'failed'
            session.save()
            CrawlLog.objects.create(
                session=session,
                level='ERROR',
                message=f'Error iniciando crawling: {str(e)}'
            )
        return {'status': 'error', 'message': str(e)}


@shared_task(bind=True)
def process_robots_txt(self, session_id: int):
    """Procesa el archivo robots.txt del dominio objetivo"""
    try:
        session = CrawlSession.objects.get(id=session_id)
        robots_url = f"https://{session.target_domain}/robots.txt"

        response = requests.get(robots_url, timeout=10)
        if response.status_code == 200:
            robots_rules = extract_robots_txt(response.text)

            # Guardar reglas en la configuración avanzada
            session.advanced_config['robots_txt'] = robots_rules
            session.save()

            CrawlLog.objects.create(
                session=session,
                level='INFO',
                message='Robots.txt procesado correctamente',
                details={'rules_found': len(robots_rules)}
            )
        else:
            CrawlLog.objects.create(
                session=session,
                level='WARNING',
                message=f'No se pudo obtener robots.txt (HTTP {response.status_code})'
            )

    except Exception as e:
        logger.error(f'Error procesando robots.txt: {str(e)}')


@shared_task(bind=True)
def process_url_queue(self, session_id: int):
    """Procesa la cola de URLs de una sesión"""
    try:
        session = CrawlSession.objects.get(id=session_id)

        if session.status != 'running':
            return {'status': 'stopped', 'reason': f'Session status: {session.status}'}

        # Obtener URLs pendientes con límite
        pending_urls = URLQueue.objects.filter(
            session=session,
            status='pending'
        ).order_by('priority', 'discovered_at')[:10]  # Procesar en lotes de 10

        if not pending_urls.exists():
            # No hay más URLs pendientes, verificar si completamos
            if session.total_urls_processed >= session.max_pages:
                complete_crawl_session.delay(session_id)
                return {'status': 'completed', 'reason': 'Max pages reached'}

            # Esperar un poco más por si aparecen nuevas URLs
            time.sleep(5)
            remaining_urls = URLQueue.objects.filter(
                session=session,
                status='pending'
            ).count()

            if remaining_urls == 0:
                complete_crawl_session.delay(session_id)
                return {'status': 'completed', 'reason': 'No more pending URLs'}

        processed_count = 0
        for url_item in pending_urls:
            if session.total_urls_processed >= session.max_pages:
                break

            # Procesar URL individual
            process_single_url.delay(session_id, url_item.id)
            processed_count += 1

            # Rate limiting
            time.sleep(1.0 / session.rate_limit)

        # Continuar procesando si hay más URLs
        if processed_count > 0:
            # Programar próximo lote
            process_url_queue.apply_async(args=[session_id], countdown=5)

        return {'status': 'processing', 'processed': processed_count}

    except CrawlSession.DoesNotExist:
        logger.error(f'Sesión {session_id} no encontrada')
        return {'status': 'error', 'message': 'Sesión no encontrada'}
    except Exception as e:
        logger.error(f'Error procesando cola de URLs: {str(e)}')
        return {'status': 'error', 'message': str(e)}


@shared_task(bind=True)
def process_single_url(self, session_id: int, url_queue_id: int):
    """Procesa una URL individual"""
    try:
        session = CrawlSession.objects.get(id=session_id)
        url_item = URLQueue.objects.get(id=url_queue_id)

        if url_item.status != 'pending':
            return {'status': 'skipped', 'reason': f'URL status: {url_item.status}'}

        url_item.status = 'processing'
        url_item.save()

        start_time = time.time()

        # Configurar headers
        headers = {
            'User-Agent': settings.CRAWLER_SETTINGS['USER_AGENT'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        # Realizar request
        response = requests.get(
            url_item.url,
            headers=headers,
            timeout=settings.CRAWLER_SETTINGS['TIMEOUT'],
            allow_redirects=session.follow_redirects,
            stream=True
        )

        response_time = time.time() - start_time

        # Actualizar información de la URL
        url_item.http_status_code = response.status_code
        url_item.response_time = response_time
        url_item.content_type = response.headers.get('content-type', '')
        url_item.processed_at = timezone.now()

        if response.status_code != 200:
            url_item.status = 'failed'
            url_item.error_message = f'HTTP {response.status_code}'
            url_item.save()

            session.total_errors += 1
            session.save()

            return {'status': 'failed', 'http_status': response.status_code}

        # Verificar tamaño del contenido
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > session.max_file_size:
            url_item.status = 'skipped'
            url_item.error_message = 'File too large'
            url_item.save()
            return {'status': 'skipped', 'reason': 'File too large'}

        # Obtener contenido
        content = response.content
        url_item.file_size = len(content)

        # Determinar tipo de archivo
        file_extension = get_file_extension(url_item.url, url_item.content_type)
        url_item.url_type = file_extension

        # Procesar según el tipo de contenido
        if file_extension == 'html':
            # Extraer nuevas URLs si no hemos alcanzado la profundidad máxima
            if url_item.depth < session.max_depth:
                extract_urls_from_html.delay(session_id, url_queue_id, content.decode('utf-8', errors='ignore'))

        # Si es un archivo de interés, guardarlo y extraer metadatos
        if is_allowed_file_type(file_extension, session.get_file_types_list()):
            save_and_extract_metadata.delay(session_id, url_queue_id, content)

        url_item.status = 'completed'
        url_item.save()

        # Actualizar estadísticas de la sesión
        session.total_urls_processed += 1
        if file_extension in session.get_file_types_list():
            session.total_files_found += 1
        session.save()

        return {'status': 'completed', 'file_type': file_extension}

    except requests.RequestException as e:
        logger.error(f'Error de request para {url_item.url}: {str(e)}')
        url_item.status = 'failed'
        url_item.error_message = str(e)
        url_item.retry_count += 1
        url_item.save()

        session.total_errors += 1
        session.save()

        # Reintentar si no hemos superado el límite
        if url_item.retry_count < settings.CRAWLER_SETTINGS['MAX_RETRIES']:
            process_single_url.apply_async(
                args=[session_id, url_queue_id],
                countdown=60 * url_item.retry_count  # Backoff exponencial
            )

        return {'status': 'failed', 'error': str(e)}

    except Exception as e:
        logger.error(f'Error procesando URL {url_item.url}: {str(e)}')
        url_item.status = 'failed'
        url_item.error_message = str(e)
        url_item.save()

        session.total_errors += 1
        session.save()

        return {'status': 'error', 'message': str(e)}


@shared_task(bind=True)
def extract_urls_from_html(self, session_id: int, url_queue_id: int, html_content: str):
    """Extrae URLs de contenido HTML"""
    try:
        session = CrawlSession.objects.get(id=session_id)
        parent_url_item = URLQueue.objects.get(id=url_queue_id)

        soup = BeautifulSoup(html_content, 'html.parser')
        base_url = parent_url_item.url
        new_urls = set()

        # Extraer URLs de diferentes elementos
        for tag in soup.find_all(['a', 'link', 'script', 'img', 'source', 'iframe']):
            url = None

            if tag.name == 'a':
                url = tag.get('href')
            elif tag.name == 'link':
                url = tag.get('href')
            elif tag.name == 'script':
                url = tag.get('src')
            elif tag.name == 'img':
                url = tag.get('src')
            elif tag.name == 'source':
                url = tag.get('src')
            elif tag.name == 'iframe':
                url = tag.get('src')

            if url:
                # Resolver URL relativa a absoluta
                absolute_url = urljoin(base_url, url)

                # Validar URL
                if is_valid_url(absolute_url, session.target_domain):
                    # Limpiar fragmentos y parámetros innecesarios
                    parsed = urlparse(absolute_url)
                    clean_url = urlunparse((
                        parsed.scheme, parsed.netloc, parsed.path,
                        parsed.params, '', ''  # Eliminar query y fragment
                    ))
                    new_urls.add(clean_url)

        # Agregar nuevas URLs a la cola
        urls_added = 0
        for url in new_urls:
            file_extension = get_file_extension(url)

            # Determinar prioridad basada en el tipo de archivo
            priority = 3  # Prioridad normal por defecto
            if file_extension in session.get_file_types_list():
                priority = 2  # Alta prioridad para archivos de interés
            elif file_extension == 'html':
                priority = 4  # Baja prioridad para HTML

            url_queue_item, created = URLQueue.objects.get_or_create(
                session=session,
                url=url,
                defaults={
                    'parent_url': base_url,
                    'depth': parent_url_item.depth + 1,
                    'url_type': file_extension,
                    'priority': priority,
                    'status': 'pending'
                }
            )

            if created:
                urls_added += 1

        # Actualizar estadísticas
        session.total_urls_discovered += urls_added
        session.save()

        if urls_added > 0:
            CrawlLog.objects.create(
                session=session,
                level='INFO',
                message=f'Descubiertas {urls_added} nuevas URLs desde {base_url}',
                details={'parent_depth': parent_url_item.depth}
            )

        return {'status': 'completed', 'urls_added': urls_added}

    except Exception as e:
        logger.error(f'Error extrayendo URLs de HTML: {str(e)}')
        return {'status': 'error', 'message': str(e)}


@shared_task(bind=True)
def save_and_extract_metadata(self, session_id: int, url_queue_id: int, content: bytes):
    """Guarda archivo y extrae metadatos"""
    try:
        session = CrawlSession.objects.get(id=session_id)
        url_item = URLQueue.objects.get(id=url_queue_id)

        # Crear hash del archivo
        file_hash = hashlib.sha256(content).hexdigest()

        # Determinar nombre de archivo
        parsed_url = urlparse(url_item.url)
        file_name = os.path.basename(parsed_url.path) or f"file_{url_item.id}"

        # Crear directorio si no existe
        storage_dir = os.path.join(settings.MEDIA_ROOT, 'crawler', str(session.id))
        os.makedirs(storage_dir, exist_ok=True)

        # Guardar archivo
        file_path = os.path.join(storage_dir, f"{file_hash}_{file_name}")
        with open(file_path, 'wb') as f:
            f.write(content)

        # Crear resultado
        result = CrawlResult.objects.create(
            session=session,
            url_queue_item=url_item,
            file_name=file_name,
            file_path=file_path,
            file_hash=file_hash,
            metadata={}  # Se llenará con la extracción de metadatos
        )

        # Marcar como que tiene metadatos pendientes
        url_item.has_metadata = False
        url_item.save()

        # Programar extracción de metadatos si está habilitada
        if session.extract_metadata:
            extract_file_metadata.delay(result.id)

        return {'status': 'completed', 'file_saved': file_path}

    except Exception as e:
        logger.error(f'Error guardando archivo: {str(e)}')
        return {'status': 'error', 'message': str(e)}


@shared_task(bind=True)
def extract_file_metadata(self, result_id: int):
    """Extrae metadatos de un archivo guardado"""
    try:
        result = CrawlResult.objects.get(id=result_id)

        # Por ahora, metadatos básicos
        # En el siguiente paso implementaremos la extracción completa
        basic_metadata = {
            'file_size': result.url_queue_item.file_size,
            'content_type': result.url_queue_item.content_type,
            'url': result.url_queue_item.url,
            'discovered_at': result.url_queue_item.discovered_at.isoformat(),
            'file_hash': result.file_hash,
        }

        result.metadata = basic_metadata
        result.save()

        # Marcar URL como que tiene metadatos
        result.url_queue_item.has_metadata = True
        result.url_queue_item.metadata_extracted_at = timezone.now()
        result.url_queue_item.save()

        return {'status': 'completed', 'metadata_fields': len(basic_metadata)}

    except Exception as e:
        logger.error(f'Error extrayendo metadatos: {str(e)}')
        return {'status': 'error', 'message': str(e)}


@shared_task(bind=True)
def complete_crawl_session(self, session_id: int):
    """Completa una sesión de crawling"""
    try:
        session = CrawlSession.objects.get(id=session_id)
        session.status = 'completed'
        session.completed_at = timezone.now()
        session.save()

        CrawlLog.objects.create(
            session=session,
            level='INFO',
            message='Crawling completado',
            details={
                'total_urls_processed': session.total_urls_processed,
                'total_files_found': session.total_files_found,
                'total_errors': session.total_errors,
                'duration_minutes': (session.completed_at - session.started_at).total_seconds() / 60
            }
        )

        return {'status': 'completed', 'session_id': session_id}

    except Exception as e:
        logger.error(f'Error completando sesión: {str(e)}')
        return {'status': 'error', 'message': str(e)}


@shared_task(bind=True)
def stop_crawl_session(self, session_id: int):
    """Detiene una sesión de crawling"""
    try:
        session = CrawlSession.objects.get(id=session_id)
        session.status = 'cancelled'
        session.completed_at = timezone.now()
        session.save()

        # Cancelar todas las URLs pendientes
        URLQueue.objects.filter(
            session=session,
            status='pending'
        ).update(status='skipped')

        CrawlLog.objects.create(
            session=session,
            level='WARNING',
            message='Crawling cancelado por el usuario'
        )

        return {'status': 'cancelled', 'session_id': session_id}

    except Exception as e:
        logger.error(f'Error cancelando sesión: {str(e)}')
        return {'status': 'error', 'message': str(e)}
