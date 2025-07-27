# core/celery.py
# CELERY_BROKER_URL = 'redis://localhost:6379/0'
# CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'


import os
from celery import Celery

# Establecer el módulo de configuración de Django para el programa 'celery'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# app = Celery('fisgon_crawler')
app = Celery('core')

# Usar Django settings.py como archivo de configuración
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodescubrir tareas en todas las apps instaladas
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


# Configuración adicional de Celery
app.conf.update(
    # Configuraciones de worker
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,

    # Configuraciones de tareas
    task_soft_time_limit=300,  # 5 minutos
    task_time_limit=600,       # 10 minutos
    task_reject_on_worker_lost=True,

    # Configuración de beat scheduler (para tareas periódicas)
    beat_schedule={
        'cleanup-failed-sessions': {
            'task': 'crawler.tasks.cleanup_failed_sessions',
            'schedule': 3600.0,  # cada hora
        },
        'update-session-stats': {
            'task': 'crawler.tasks.update_session_statistics',
            'schedule': 300.0,   # cada 5 minutos
        },
    },
)
