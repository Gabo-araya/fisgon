from django.apps import AppConfig


class CrawlerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crawler'
    verbose_name = 'Sistema de Crawling'

    def ready(self):
        # Importar signals si los hay
        try:
            import crawler.signals
        except ImportError:
            pass
