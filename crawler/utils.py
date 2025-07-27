import re
import validators
import tldextract
from urllib.parse import urlparse, urljoin, urlunparse
from typing import List, Dict, Set, Optional
from urllib.robotparser import RobotFileParser
from django.conf import settings
import mimetypes
import logging

logger = logging.getLogger('crawler')

def is_valid_url(url: str, allowed_domain: str = None) -> bool:
    '''
    Valida si una URL es válida y pertenece al dominio permitido
    '''
    try:
        # Validación básica de URL
        if not validators.url(url):
            return False

        parsed = urlparse(url)
        # Verificar que tenga esquema HTTP/HTTPS
        if parsed.scheme not in ['http', 'https']:
            return False

        # Verificar que tenga dominio válido
        if not parsed.netloc:
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
    '''
    Determina la extensión de archivo basada en la URL y content-type
    '''
    try:
        # Primero intentar extraer de la URL
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Buscar extensión al final del path
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
    '''
    Verifica si un tipo de archivo está en la lista de tipos permitidos
    '''

    # extension = get_file_extension(url)
    # return extension in allowed_types if extension else False

    if not allowed_types:
        return True  # Si no hay restricciones, permitir todo

    return file_extension.lower() in [t.lower() for t in allowed_types]


def extract_robots_txt(robots_content: str) -> Dict[str, List[str]]:
    '''
    Extrae reglas del archivo robots.txt
    '''
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



def extract_robots_txt2(domain: str) -> dict:
    '''
    Extrae y parsea el archivo robots.txt de un dominio
    '''
    robots_info = {
        'allowed': [],
        'disallowed': [],
        'crawl_delay': None,
        'sitemap_urls': []
    }

    try:
        robots_url = f"https://{domain}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()

        # Obtener delay de crawling si existe
        crawl_delay = rp.crawl_delay("*")
        if crawl_delay:
            robots_info['crawl_delay'] = crawl_delay

        # Para obtener más detalles, tendríamos que parsear manualmente
        # el contenido del robots.txt ya que RobotFileParser es limitado

        return robots_info
    except Exception as e:
        logger.warning(f"Error extrayendo robots.txt para {domain}: {str(e)}")
        return robots_info



# def should_respect_robots_txt(url: str, robots_rules: Dict[str, List[str]]) -> bool:
#     '''
#     Verifica si una URL debería ser respetada según robots.txt
#     '''
#     if not robots_rules:
#         return True

#     try:
#         parsed = urlparse(url)
#         path = parsed.path

#         # Verificar reglas de allow primero (más específicas)
#         for allow_pattern in robots_rules.get('allow', []):
#             if path.startswith(allow_pattern):
#                 return True

#         # Verificar reglas de disallow
#         for disallow_pattern in robots_rules.get('disallow', []):
#             if disallow_pattern == '/':
#                 return False  # Todo el sitio está bloqueado
#             elif path.startswith(disallow_pattern):
#                 return False

#         return True

#     except Exception as e:
#         logger.warning(f"Error verificando robots.txt para {url}: {str(e)}")
#         return True  # En caso de error, permitir


def should_respect_robots_txt(url: str, user_agent: str = "*") -> bool:
    '''
    Verifica si se puede acceder a una URL según robots.txt
    '''
    try:
        domain = get_domain_from_url(url)
        robots_url = f"https://{domain}/robots.txt"

        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()

        return rp.can_fetch(user_agent, url)

    except Exception as e:
        # Si hay error, permitir el acceso por defecto
        logger.warning(f"Error verificando robots.txt para {url}: {str(e)}")
        return True



def clean_url(url: str) -> str:
    '''
    Limpia y normaliza una URL
    '''
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


def normalize_url(url: str, base_url: str = None) -> str:
    '''
    Normaliza una URL eliminando fragmentos y parámetros innecesarios
    '''
    try:
        # Convertir URL relativa a absoluta si se proporciona base_url
        if base_url and not url.startswith(('http://', 'https://')):
            url = urljoin(base_url, url)

        parsed = urlparse(url)

        # Reconstruir URL sin fragmentos
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),  # Dominio en minúsculas
            parsed.path,
            parsed.params,
            parsed.query,
            ''  # Remover fragmento
        ))

        return normalized
    except Exception:
        return url


def extract_domain_from_url(url: str) -> str:
    '''
    Extrae el dominio principal de una URL
    '''
    try:
        extracted = tldextract.extract(url)
        return f"{extracted.domain}.{extracted.suffix}"
    except Exception as e:
        logger.warning(f"Error extrayendo dominio de {url}: {str(e)}")
        return ""


def get_domain_from_url(url: str) -> str:
    '''
    Extrae el dominio principal de una URL
    '''
    try:
        extracted = tldextract.extract(url)
        return f"{extracted.domain}.{extracted.suffix}"
    except Exception:
        return ""


def is_binary_file(content_type: str) -> bool:
    '''
    Determina si un content-type corresponde a un archivo binario
    '''
    text_types = [
        'text/', 'application/json', 'application/xml',
        'application/javascript', 'application/x-javascript'
    ]

    content_type = content_type.lower()

    for text_type in text_types:
        if content_type.startswith(text_type):
            return False

    return True


def is_binary_content(content_type: str) -> bool:
    '''
    Determina si un content-type corresponde a contenido binario
    '''
    text_types = [
        'text/', 'application/json', 'application/xml',
        'application/javascript', 'application/html'
    ]

    return not any(content_type.startswith(t) for t in text_types)



def is_same_domain(url1: str, url2: str) -> bool:
    '''
    Verifica si dos URLs pertenecen al mismo dominio
    '''
    return get_domain_from_url(url1) == get_domain_from_url(url2)



def get_url_depth(url: str, base_url: str) -> int:
    '''
    Calcula la profundidad de una URL relativa a una URL base
    '''
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



def get_url_priority(url: str, file_types_priority: dict = None) -> int:
    '''
    Calcula la prioridad de una URL basada en su tipo
    '''
    if not file_types_priority:
        file_types_priority = {
            'pdf': 1,
            'doc': 2, 'docx': 2,
            'xls': 2, 'xlsx': 2,
            'ppt': 2, 'pptx': 2,
            'jpg': 3, 'jpeg': 3, 'png': 3, 'gif': 3,
            'mp3': 4, 'mp4': 4,
            'html': 5,
            'other': 6
        }

    extension = get_file_extension(url)
    return file_types_priority.get(extension, file_types_priority['other'])



def estimate_file_size_from_headers(headers: dict) -> int:
    '''
    Estima el tamaño de archivo desde headers HTTP
    '''
    try:
        content_length = headers.get('content-length') or headers.get('Content-Length')
        if content_length:
            return int(content_length)
    except (ValueError, TypeError):
        pass
    return 0



def format_file_size(size_bytes: int) -> str:
    '''
    Formatea el tamaño de archivo en formato legible
    '''
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)

    return f"{s} {size_names[i]}"


def is_likely_file_url(url: str) -> bool:
    '''
    Determina si una URL probablemente apunta a un archivo descargable
    '''
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
    '''
    Sanitiza un nombre de archivo para guardarlo de forma segura
    '''
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



def clean_filename(filename: str) -> str:
    '''
    Limpia un nombre de archivo eliminando caracteres peligrosos
    '''
    # Remover caracteres peligrosos
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)

    # Limitar longitud
    if len(cleaned) > 255:
        name, ext = cleaned.rsplit('.', 1) if '.' in cleaned else (cleaned, '')
        cleaned = name[:255-len(ext)-1] + '.' + ext if ext else name[:255]

    return cleaned



def extract_urls_from_html(html_content: str, base_url: str) -> list:
    '''
    Extrae URLs de contenido HTML
    '''
    from bs4 import BeautifulSoup

    urls = []
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Enlaces en tags <a>
        for link in soup.find_all('a', href=True):
            url = normalize_url(link['href'], base_url)
            if is_valid_url(url):
                urls.append(url)

        # Enlaces en tags <link>
        for link in soup.find_all('link', href=True):
            url = normalize_url(link['href'], base_url)
            if is_valid_url(url):
                urls.append(url)

        # Scripts
        for script in soup.find_all('script', src=True):
            url = normalize_url(script['src'], base_url)
            if is_valid_url(url):
                urls.append(url)

        # Imágenes
        for img in soup.find_all('img', src=True):
            url = normalize_url(img['src'], base_url)
            if is_valid_url(url):
                urls.append(url)

        # Recursos multimedia
        for media in soup.find_all(['video', 'audio'], src=True):
            url = normalize_url(media['src'], base_url)
            if is_valid_url(url):
                urls.append(url)

        # Source tags dentro de video/audio
        for source in soup.find_all('source', src=True):
            url = normalize_url(source['src'], base_url)
            if is_valid_url(url):
                urls.append(url)

    except Exception as e:
        logger.error(f"Error extrayendo URLs del HTML: {str(e)}")

    return list(set(urls))  # Eliminar duplicados



def sanitize_metadata_value(value) -> str:
    '''
    Sanitiza valores de metadatos para almacenamiento seguro
    '''
    if value is None:
        return ""

    # Convertir a string y limpiar
    str_value = str(value).strip()

    # Limitar longitud
    if len(str_value) > 1000:
        str_value = str_value[:1000] + "..."

    return str_value



class CrawlerRateLimiter:
    '''
    Implementa rate limiting para requests
    '''
    def __init__(self, rate_limit: float):
        self.rate_limit = rate_limit  # requests per second
        self.last_request_time = 0

    def wait_if_needed(self):
        '''
        Espera el tiempo necesario para respetar el rate limit
        '''
        import time

        if self.rate_limit <= 0:
            return

        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 1.0 / self.rate_limit

        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()
