import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from crawler.models import CrawlSession
from crawler.tasks import start_crawl_session


class Command(BaseCommand):
    help = 'Inicia una sesión de crawling desde línea de comandos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--session-id',
            type=int,
            help='ID de la sesión a iniciar',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Nombre de usuario propietario de la sesión',
        )
        parser.add_argument(
            '--domain',
            type=str,
            help='Dominio a crawlear (para crear nueva sesión)',
        )
        parser.add_argument(
            '--url',
            type=str,
            help='URL inicial (para crear nueva sesión)',
        )
        parser.add_argument(
            '--name',
            type=str,
            help='Nombre de la sesión (para crear nueva sesión)',
        )

    def handle(self, *args, **options):
        session_id = options.get('session_id')

        if session_id:
            # Iniciar sesión existente
            try:
                session = CrawlSession.objects.get(id=session_id)
                if session.status != 'pending':
                    raise CommandError(f'La sesión {session_id} no está en estado pendiente')

                self.stdout.write(f'Iniciando sesión {session_id}: {session.name}')
                start_crawl_session.delay(session_id)
                self.stdout.write(
                    self.style.SUCCESS(f'Sesión {session_id} iniciada exitosamente')
                )

            except CrawlSession.DoesNotExist:
                raise CommandError(f'La sesión {session_id} no existe')

        else:
            # Crear nueva sesión
            user_name = options.get('user')
            domain = options.get('domain')
            url = options.get('url')
            name = options.get('name')

            if not all([user_name, domain, url, name]):
                raise CommandError(
                    'Para crear nueva sesión se requieren: --user, --domain, --url, --name'
                )

            try:
                user = User.objects.get(username=user_name)

                session = CrawlSession.objects.create(
                    name=name,
                    user=user,
                    target_domain=domain,
                    target_url=url,
                    status='pending'
                )

                self.stdout.write(f'Sesión creada con ID: {session.id}')
                self.stdout.write(f'Iniciando crawling de {domain}...')

                start_crawl_session.delay(session.id)
                self.stdout.write(
                    self.style.SUCCESS(f'Sesión {session.id} iniciada exitosamente')
                )

            except User.DoesNotExist:
                raise CommandError(f'El usuario {user_name} no existe')
            except Exception as e:
                raise CommandError(f'Error creando sesión: {str(e)}')
