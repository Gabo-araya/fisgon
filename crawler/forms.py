from django import forms
from django.conf import settings
from .models import CrawlSession
import validators
import tldextract

class CreateCrawlSessionForm(forms.ModelForm):
    """Formulario para crear una nueva sesión de crawling"""

    file_types = forms.MultipleChoiceField(
        choices=[
            ('pdf', 'PDF'),
            ('doc', 'Word (.doc)'),
            ('docx', 'Word (.docx)'),
            ('xls', 'Excel (.xls)'),
            ('xlsx', 'Excel (.xlsx)'),
            ('ppt', 'PowerPoint (.ppt)'),
            ('pptx', 'PowerPoint (.pptx)'),
            ('odt', 'OpenDocument Text'),
            ('ods', 'OpenDocument Spreadsheet'),
            ('odp', 'OpenDocument Presentation'),
            ('jpg', 'JPEG'),
            ('jpeg', 'JPEG'),
            ('png', 'PNG'),
            ('gif', 'GIF'),
            ('tiff', 'TIFF'),
            ('mp3', 'MP3'),
            ('mp4', 'MP4'),
            ('xml', 'XML'),
            ('json', 'JSON'),
        ],
        widget=forms.CheckboxSelectMultiple,
        required=False,
        initial=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'],
        help_text="Selecciona los tipos de archivo que deseas buscar y analizar"
    )

    class Meta:
        model = CrawlSession
        fields = [
            'name', 'target_url', 'max_depth', 'rate_limit',
            'max_pages', 'max_file_size', 'respect_robots_txt',
            'follow_redirects', 'extract_metadata'
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Crawling de documentos de example.com'
            }),
            'target_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com'
            }),
            'max_depth': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10,
                'value': 3
            }),
            'rate_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0.1,
                'max': 10.0,
                'step': 0.1,
                'value': 1.0
            }),
            'max_pages': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'value': 0,
                'placeholder': '0 = Sin límite'
            }),
            'max_file_size': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1048576,  # 1MB
                'max': 104857600,  # 100MB
                'value': 52428800,  # 50MB
                'step': 1048576
            }),
            'respect_robots_txt': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'follow_redirects': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'extract_metadata': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

        labels = {
            'name': 'Nombre de la sesión',
            'target_url': 'URL objetivo',
            'max_depth': 'Profundidad máxima',
            'rate_limit': 'Límite de velocidad (req/seg)',
            'max_pages': 'Máximo de páginas',
            'max_file_size': 'Tamaño máximo de archivo (bytes)',
            'respect_robots_txt': 'Respetar robots.txt',
            'follow_redirects': 'Seguir redirecciones',
            'extract_metadata': 'Extraer metadatos',
        }

        help_texts = {
            'name': 'Nombre descriptivo para identificar esta sesión de crawling',
            'target_url': 'URL inicial desde donde comenzar el crawling',
            'max_depth': 'Niveles de profundidad a explorar desde la URL inicial',
            'rate_limit': 'Número de requests por segundo (para evitar sobrecargar el servidor)',
            'max_pages': 'Número máximo de páginas a procesar (0 = sin límite)',
            'max_file_size': 'Tamaño máximo de archivo a descargar (en bytes)',
            'respect_robots_txt': 'Respetar las restricciones del archivo robots.txt del sitio',
            'follow_redirects': 'Seguir automáticamente las redirecciones HTTP',
            'extract_metadata': 'Extraer metadatos de los archivos encontrados',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Configurar valores por defecto desde settings
        crawler_settings = getattr(settings, 'CRAWLER_SETTINGS', {})

        if not self.instance.pk:  # Solo para nuevas instancias
            self.fields['max_depth'].initial = crawler_settings.get('MAX_DEPTH', 3)
            self.fields['rate_limit'].initial = crawler_settings.get('DEFAULT_RATE_LIMIT', 1.0)
            self.fields['max_pages'].initial = crawler_settings.get('MAX_PAGES', 0)
            self.fields['max_file_size'].initial = crawler_settings.get('MAX_FILE_SIZE', 52428800)

        # Personalizar widget de file_types
        self.fields['file_types'].widget.attrs.update({'class': 'form-check-input'})

    def clean_target_url(self):
        url = self.cleaned_data['target_url']

        # Validar formato de URL
        if not validators.url(url):
            raise forms.ValidationError("Por favor ingresa una URL válida.")

        # Verificar que sea HTTP o HTTPS
        if not url.startswith(('http://', 'https://')):
            raise forms.ValidationError("La URL debe comenzar con http:// o https://")

        return url

    def clean_max_depth(self):
        depth = self.cleaned_data['max_depth']

        if depth < 1:
            raise forms.ValidationError("La profundidad debe ser al menos 1.")

        if depth > 10:
            raise forms.ValidationError("La profundidad máxima permitida es 10.")

        return depth

    def clean_rate_limit(self):
        rate = self.cleaned_data['rate_limit']

        if rate <= 0:
            raise forms.ValidationError("El límite de velocidad debe ser mayor a 0.")

        if rate > 10:
            raise forms.ValidationError("El límite máximo de velocidad es 10 req/seg.")

        return rate

    def clean_max_pages(self):
        pages = self.cleaned_data['max_pages']

        if pages < 0:
            raise forms.ValidationError("El número de páginas no puede ser negativo. Usar 0 para sin límite.")

        return pages

    def clean_max_file_size(self):
        size = self.cleaned_data['max_file_size']

        if size < 1024:  # 1KB mínimo
            raise forms.ValidationError("El tamaño mínimo de archivo es 1KB.")

        if size > 104857600:  # 100MB máximo
            raise forms.ValidationError("El tamaño máximo de archivo permitido es 100MB.")

        return size

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Extraer dominio de la URL
        try:
            extracted = tldextract.extract(instance.target_url)
            instance.target_domain = f"{extracted.domain}.{extracted.suffix}"
        except Exception:
            # Fallback manual
            from urllib.parse import urlparse
            parsed = urlparse(instance.target_url)
            instance.target_domain = parsed.netloc

        # Guardar tipos de archivo seleccionados
        file_types = self.cleaned_data.get('file_types', [])
        instance.set_file_types_list(file_types)

        if commit:
            instance.save()

        return instance


class CrawlSessionFilterForm(forms.Form):
    """Formulario para filtrar sesiones de crawling"""

    STATUS_CHOICES = [
        ('', 'Todos los estados'),
        ('pending', 'Pendiente'),
        ('running', 'Ejecutándose'),
        ('paused', 'Pausado'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
        ('cancelled', 'Cancelado'),
    ]

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    domain = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filtrar por dominio...'
        })
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    user = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filtrar por usuario...'
        })
    )


class CrawlSessionSettingsForm(forms.ModelForm):
    """Formulario para actualizar configuraciones de una sesión activa"""

    class Meta:
        model = CrawlSession
        fields = ['rate_limit', 'max_pages', 'max_file_size']

        widgets = {
            'rate_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0.1,
                'max': 10.0,
                'step': 0.1
            }),
            'max_pages': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': '0 = Sin límite'
            }),
            'max_file_size': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1048576,
                'max': 104857600,
                'step': 1048576
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        # Validar que la sesión pueda ser modificada
        if self.instance and self.instance.status not in ['pending', 'running', 'paused']:
            raise forms.ValidationError(
                "Solo se pueden modificar sesiones pendientes, en ejecución o pausadas."
            )

        return cleaned_data


class BulkActionForm(forms.Form):
    """Formulario para acciones en lote sobre sesiones"""

    ACTION_CHOICES = [
        ('', 'Seleccionar acción...'),
        ('pause', 'Pausar'),
        ('resume', 'Reanudar'),
        ('cancel', 'Cancelar'),
        ('delete', 'Eliminar'),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    session_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )

    def clean_session_ids(self):
        session_ids = self.cleaned_data['session_ids']

        try:
            # Convertir string separado por comas a lista de enteros
            ids = [int(id.strip()) for id in session_ids.split(',') if id.strip()]

            if not ids:
                raise forms.ValidationError("Debe seleccionar al menos una sesión.")

            # Verificar que todas las sesiones existan
            from .models import CrawlSession
            existing_count = CrawlSession.objects.filter(id__in=ids).count()

            if existing_count != len(ids):
                raise forms.ValidationError("Algunas sesiones seleccionadas no existen.")

            return ids

        except ValueError:
            raise forms.ValidationError("IDs de sesión inválidos.")

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        session_ids = cleaned_data.get('session_ids', [])

        if action and session_ids:
            from .models import CrawlSession

            sessions = CrawlSession.objects.filter(id__in=session_ids)

            # Validar según la acción
            if action == 'pause':
                invalid_sessions = sessions.exclude(status='running')
                if invalid_sessions.exists():
                    raise forms.ValidationError(
                        "Solo se pueden pausar sesiones en ejecución."
                    )

            elif action == 'resume':
                invalid_sessions = sessions.exclude(status='paused')
                if invalid_sessions.exists():
                    raise forms.ValidationError(
                        "Solo se pueden reanudar sesiones pausadas."
                    )

            elif action == 'cancel':
                invalid_sessions = sessions.exclude(status__in=['pending', 'running', 'paused'])
                if invalid_sessions.exists():
                    raise forms.ValidationError(
                        "Solo se pueden cancelar sesiones activas."
                    )

        return cleaned_data
