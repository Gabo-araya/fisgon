import re
import validators
import tldextract
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Set, Optional
import mimetypes
import logging

logger = logging.getLogger('crawler')

def is_valid_url(url: str, allowed_domain: str = None) -> bool:
    """
    Valida si una URL es válida y pertenece al dominio permitido
    """
    try:
        # Validación básica de URL
        if not validators.url(url):
            return False

        parsed = urlparse(url)

        # Verificar esquema
        if parsed.scheme not in ['http', 'https']:
            return False

        # Verificar dominio si se especifica
        if allowed_domain:
            extracted = tldextract.extract(url)
            url_domain = f"{extracted.domain}.{extracted.suffix}"

            if url_domain != allowed_domain:
                return False

        # Filtrar URLs problemáticas
        problematic_patterns = [
            r'javascript:',
            r'mailto:',
            r'tel:',
            r'ftp:',
            r'#',
            r'\?.*logout',
            r'\?.*signout',
            r'\/logout',
            r'\/signout',
        ]

        for pattern in problematic_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False

        return True

    except Exception as e:
        logger.warning(f"Error validando URL {url}: {str(e)}")
        return False


def get_file_extension(url: str, content_type: str = None) -> str:
    """
    Determina la extensión de archivo basada en la URL y content-type
    """
    try:
        # Primero intentar extraer de la URL
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Buscar extensión en la URL
        if '.' in path:
            extension = path.split('.')[-1]

            # Limpiar parámetros
            extension = extension.split('?')[0].split('#')[0]

            # Validar extensiones conocidas
            known_extensions = [
                'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                'odt', 'ods', 'odp', 'jpg', 'jpeg', 'png', 'gif',
                'tiff', 'mp3', 'mp4', 'xml', 'json', 'txt', 'csv'
            ]

            if extension in known_extensions:
                return extension

        # Si no hay extensión clara, usar content-type
        if content_type:
            content_type = content_type.lower().split(';')[0].strip()

            content_type_map = {
                'application/pdf': 'pdf',
                'application/msword': 'doc',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
                'application/vnd.ms-excel': 'xls',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
                'application/vnd.ms-powerpoint': 'ppt',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
                'application/vnd.oasis.opendocument.text': 'odt',
                'application/vnd.oasis.opendocument.spreadsheet': 'ods',
                'application/vnd.oasis.opendocument.presentation': 'odp',
                'image/jpeg': 'jpg',
                'image/png': 'png',
                'image/gif': 'gif',
                'image/tiff': 'tiff',
                'audio/mpeg': 'mp3',
                'video/mp4': 'mp4',
                'application/xml': 'xml',
                'text/xml': 'xml',
                'application/json': 'json',
                'text/html': 'html',
                'text/plain': 'txt',
                'text/csv': 'csv',
            }

            if content_type in content_type_map:
                return content_type_map[content_type]

        # Por defecto, asumir HTML si no se puede determinar
        return 'html'

    except Exception as e:
        logger.warning(f"Error determinando extensión para {url}: {str(e)}")
        return 'unknown'


def is_allowed_file_type(file_extension: str, allowed_types: List[str]) -> bool:
    """
    Verifica si un tipo de archivo está en la lista de tipos permitidos
    """
    if not allowed_types:
        return True  # Si no hay restricciones, permitir todo

    return file_extension.lower() in [t.lower() for t in allowed_types]


def extract_robots_txt(robots_content: str) -> Dict[str, List[str]]:
    """
    Extrae reglas del archivo robots.txt
    """
    rules = {
        'disallow': [],
        'allow': [],
        'sitemap': [],
        'crawl_delay': None
    }

    try:
        current_user_agent = None
        applies_to_us = False

        for line in robots_content.split('\n'):
            line = line.strip()

            if line.startswith('#') or not line:
                continue

            if ':' not in line:
                continue

            directive, value = line.split(':', 1)
            directive = directive.strip().lower()
            value = value.strip()

            if directive == 'user-agent':
                current_user_agent = value.lower()
                applies_to_us = (current_user_agent == '*' or
                               'fisgon' in current_user_agent or
                               'crawler' in current_user_agent)

            elif applies_to_us:
                if directive == 'disallow' and value:
                    rules['disallow'].append(value)
                elif directive == 'allow' and value:
                    rules['allow'].append(value)
                elif directive == 'crawl-delay':
                    try:
                        rules['crawl_delay'] = float(value)
                    except ValueError:
                        pass

            elif directive == 'sitemap':
                rules['sitemap'].append(value)

    except Exception as e:
        logger.warning(f"Error procesando robots.txt: {str(e)}")

    return rules


def should_respect_robots_txt(url: str, robots_rules: Dict[str, List[str]]) -> bool:
    """
    Verifica si una URL debería ser respetada según robots.txt
    """
    if not robots_rules:
        return True

    try:
        parsed = urlparse(url)
        path = parsed.path

        # Verificar reglas de allow primero (más específicas)
        for allow_pattern in robots_rules.get('allow', []):
            if path.startswith(allow_pattern):
                return True

        # Verificar reglas de disallow
        for disallow_pattern in robots_rules.get('disallow', []):
            if disallow_pattern == '/':
                return False  # Todo el sitio está bloqueado
            elif path.startswith(disallow_pattern):
                return False

        return True

    except Exception as e:
        logger.warning(f"Error verificando robots.txt para {url}: {str(e)}")
        return True  # En caso de error, permitir


def clean_url(url: str) -> str:
    """
    Limpia y normaliza una URL
    """
    try:
        parsed = urlparse(url)

        # Reconstruir URL sin fragmentos y con query limpio
        clean_query = ''  # Por ahora, eliminar todos los parámetros query

        from urllib.parse import urlunparse
        cleaned = urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            clean_query,
            ''  # Sin fragmento
        ))

        # Eliminar barras dobles
        cleaned = re.sub(r'/+', '/', cleaned.replace('://', '://'))

        return cleaned

    except Exception as e:
        logger.warning(f"Error limpiando URL {url}: {str(e)}")
        return url


def extract_domain_from_url(url: str) -> str:
    """
    Extrae el dominio principal de una URL
    """
    try:
        extracted = tldextract.extract(url)
        return f"{extracted.domain}.{extracted.suffix}"
    except Exception as e:
        logger.warning(f"Error extrayendo dominio de {url}: {str(e)}")
        return ""


def is_binary_file(content_type: str) -> bool:
    """
    Determina si un content-type corresponde a un archivo binario
    """
    text_types = [
        'text/', 'application/json', 'application/xml',
        'application/javascript', 'application/x-javascript'
    ]

    content_type = content_type.lower()

    for text_type in text_types:
        if content_type.startswith(text_type):
            return False

    return True


def get_url_depth(url: str, base_url: str) -> int:
    """
    Calcula la profundidad de una URL relativa a una URL base
    """
    try:
        base_parsed = urlparse(base_url)
        url_parsed = urlparse(url)

        if base_parsed.netloc != url_parsed.netloc:
            return -1  # Dominio diferente

        base_parts = [p for p in base_parsed.path.split('/') if p]
        url_parts = [p for p in url_parsed.path.split('/') if p]

        return len(url_parts) - len(base_parts)

    except Exception as e:
        logger.warning(f"Error calculando profundidad: {str(e)}")
        return 0


def format_file_size(size_bytes: int) -> str:
    """
    Formatea el tamaño de archivo en formato legible
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)

    return f"{s} {size_names[i]}"


def is_likely_file_url(url: str) -> bool:
    """
    Determina si una URL probablemente apunta a un archivo descargable
    """
    try:
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Extensiones que probablemente son archivos
        file_extensions = [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.odt', '.ods', '.odp', '.zip', '.rar', '.tar', '.gz',
            '.jpg', '.jpeg', '.png', '.gif', '.tiff', '.bmp',
            '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv',
            '.txt', '.csv', '.xml', '.json'
        ]

        for ext in file_extensions:
            if path.endswith(ext):
                return True

        # Patrones de URL que suelen ser archivos
        file_patterns = [
            r'/download/',
            r'/files/',
            r'/documents/',
            r'/uploads/',
            r'/attachments/',
            r'\.pdf\?',
            r'\.doc\?',
            r'\.xlsx?\?'
        ]

        for pattern in file_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True

        return False

    except Exception as e:
        logger.warning(f"Error verificando si es archivo: {str(e)}")
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitiza un nombre de archivo para guardarlo de forma segura
    """
    try:
        # Eliminar caracteres problemáticos
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

        # Limitar longitud
        if len(filename) > 200:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:190] + ('.' + ext if ext else '')

        # Asegurar que no esté vacío
        if not filename.strip():
            filename = 'unknown_file'

        return filename.strip()

    except Exception as e:
        logger.warning(f"Error sanitizando filename: {str(e)}")
        return 'sanitized_file'
