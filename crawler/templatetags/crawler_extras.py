from django import template
from django.utils.safestring import mark_safe
from django.utils import timezone
import json

register = template.Library()


@register.filter
def file_size_format(bytes_value):
    """
    Convierte bytes a formato legible (KB, MB, GB)
    """
    if not bytes_value:
        return "0 B"

    try:
        bytes_value = int(bytes_value)
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024 * 1024:
            return f"{bytes_value / 1024:.1f} KB"
        elif bytes_value < 1024 * 1024 * 1024:
            return f"{bytes_value / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_value / (1024 * 1024 * 1024):.1f} GB"
    except (ValueError, TypeError):
        return "0 B"


@register.filter
def status_badge_class(status):
    """
    Retorna la clase CSS para el badge de estado
    """
    status_classes = {
        'pending': 'bg-warning',
        'running': 'bg-primary',
        'paused': 'bg-info',
        'completed': 'bg-success',
        'failed': 'bg-danger',
        'cancelled': 'bg-secondary'
    }
    return status_classes.get(status, 'bg-secondary')


@register.filter
def status_icon(status):
    """
    Retorna el ícono Bootstrap para el estado
    """
    status_icons = {
        'pending': 'bi-clock',
        'running': 'bi-play-circle',
        'paused': 'bi-pause-circle',
        'completed': 'bi-check-circle',
        'failed': 'bi-x-circle',
        'cancelled': 'bi-stop-circle'
    }
    return status_icons.get(status, 'bi-question-circle')


@register.filter
def progress_bar_class(percentage):
    """
    Retorna la clase de color para la barra de progreso
    """
    try:
        percentage = float(percentage)
        if percentage < 30:
            return 'bg-danger'
        elif percentage < 70:
            return 'bg-warning'
        else:
            return 'bg-success'
    except (ValueError, TypeError):
        return 'bg-secondary'


@register.filter
def time_ago(datetime_value):
    """
    Retorna tiempo transcurrido en formato legible
    """
    if not datetime_value:
        return "Nunca"

    now = timezone.now()
    diff = now - datetime_value

    if diff.days > 0:
        return f"Hace {diff.days} día{'s' if diff.days != 1 else ''}"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"Hace {hours} hora{'s' if hours != 1 else ''}"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"Hace {minutes} minuto{'s' if minutes != 1 else ''}"
    else:
        return "Hace un momento"


@register.filter
def duration_format(start_time, end_time=None):
    """
    Formatea duración entre dos fechas
    """
    if not start_time:
        return "N/A"

    if not end_time:
        end_time = timezone.now()

    duration = end_time - start_time
    total_seconds = int(duration.total_seconds())

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


@register.filter
def json_pretty(value):
    """
    Formatea JSON de manera legible
    """
    try:
        if isinstance(value, str):
            value = json.loads(value)
        return mark_safe(f"<pre>{json.dumps(value, indent=2, ensure_ascii=False)}</pre>")
    except (json.JSONDecodeError, TypeError):
        return str(value)


@register.filter
def truncate_url(url, length=50):
    """
    Trunca una URL manteniendo el dominio visible
    """
    if len(url) <= length:
        return url

    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc

    if len(domain) >= length - 3:
        return domain[:length-3] + "..."

    remaining = length - len(domain) - 3
    path = parsed.path + ("?" + parsed.query if parsed.query else "")

    if len(path) > remaining:
        path = path[:remaining] + "..."

    return domain + path


@register.filter
def file_type_icon(file_type):
    """
    Retorna el ícono apropiado para el tipo de archivo
    """
    icons = {
        'pdf': 'bi-file-earmark-pdf text-danger',
        'doc': 'bi-file-earmark-word text-primary',
        'docx': 'bi-file-earmark-word text-primary',
        'xls': 'bi-file-earmark-excel text-success',
        'xlsx': 'bi-file-earmark-excel text-success',
        'ppt': 'bi-file-earmark-ppt text-warning',
        'pptx': 'bi-file-earmark-ppt text-warning',
        'jpg': 'bi-file-earmark-image text-info',
        'jpeg': 'bi-file-earmark-image text-info',
        'png': 'bi-file-earmark-image text-info',
        'gif': 'bi-file-earmark-image text-info',
        'mp3': 'bi-file-earmark-music text-purple',
        'mp4': 'bi-file-earmark-play text-dark',
        'html': 'bi-file-earmark-code text-secondary',
        'xml': 'bi-file-earmark-code text-secondary',
        'json': 'bi-file-earmark-code text-secondary',
    }
    return icons.get(file_type.lower(), 'bi-file-earmark text-muted')


@register.simple_tag
def crawler_stats_card(title, value, icon, color="primary"):
    """
    Genera una tarjeta de estadísticas
    """
    return mark_safe(f"""
    <div class="col-md-3">
        <div class="card info-card">
            <div class="card-body">
                <h5 class="card-title">{title}</h5>
                <div class="d-flex align-items-center">
                    <div class="card-icon rounded-circle d-flex align-items-center justify-content-center">
                        <i class="bi {icon} text-{color}"></i>
                    </div>
                    <div class="ps-3">
                        <h6>{value}</h6>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """)


@register.inclusion_tag('crawler/widgets/progress_bar.html')
def progress_bar(percentage, show_text=True, height="20px"):
    """
    Template tag para mostrar barra de progreso
    """
    return {
        'percentage': percentage,
        'show_text': show_text,
        'height': height,
        'color_class': progress_bar_class(percentage)
    }
