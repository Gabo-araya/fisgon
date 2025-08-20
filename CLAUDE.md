# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fisgón is a Django web application for metadata web crawling. It discovers files across target domains and extracts comprehensive metadata for analysis. The system includes user authentication, crawler session management, asynchronous task processing, and real-time updates.

## Architecture

### Core Applications
- `core/` - Django project configuration, ASGI/WSGI, Celery setup
- `panel/` - User management and dashboard functionality  
- `crawler/` - Main crawling engine, models, tasks, and views

### Key Technologies
- **Backend**: Django 5.2.4 with PostgreSQL/SQLite support
- **Async Processing**: Celery with Redis broker for crawling tasks
- **Real-time**: Django Channels with WebSockets for live updates
- **Crawling**: Scrapy, requests, BeautifulSoup for web scraping
- **Metadata**: PyPDF2, python-docx, Pillow, ExifRead for file analysis

### Data Models
- `CrawlSession` - Crawling configuration and session state
- `URLQueue` - URLs discovered and processing status
- `CrawlResult` - Files found and extracted metadata
- `CrawlLog` - Event logging during crawling

## Development Commands

### Environment Setup
```bash
# Activate virtual environment
source env/bin/activate

# Install dependencies
python3 -m pip install -r requirements.txt

# Environment configuration
# Copy .env example from readme.md and configure
```

### Database Operations
```bash
# Create migrations
python3 manage.py makemigrations

# Apply migrations  
python3 manage.py migrate

# Create superuser
python3 manage.py createsuperuser
```

### Development Server
```bash
# Start Django server
python3 manage.py runserver

# Start on specific port
python3 manage.py runserver 8000

# Collect static files
python3 manage.py collectstatic
```

### Celery and Redis
```bash
# Start Redis (required for Celery)
redis-server

# Start Celery worker
celery -A core worker --loglevel=info

# Start Celery beat (scheduled tasks)
celery -A core beat --loglevel=info

# Monitor tasks with Flower
celery -A core flower
```

### Crawler Operations
```bash
# Start crawler via management command
python3 manage.py start_crawler

# Check crawler logs
tail -f logs/crawler.log
```

## Configuration

### Environment Variables (.env)
Key variables that should be configured:
- `SECRET_KEY` - Django secret key
- `DEBUG` - Development mode flag
- `CELERY_BROKER_URL` - Redis URL for Celery
- `CELERY_RESULT_BACKEND` - Redis URL for results

### Crawler Settings
Located in `core/settings.py` under `CRAWLER_SETTINGS`:
- Rate limiting, max depth, file size limits
- Allowed file types for extraction
- User agent and robots.txt compliance

## Testing and Quality

### Running Tests
```bash
# Run all tests
python3 manage.py test

# Run specific app tests
python3 manage.py test crawler
python3 manage.py test panel
```

### Code Quality
The project uses Django's built-in testing framework. No external linters are configured.

## Common Workflows

### Creating a Crawl Session
1. Navigate to crawler dashboard
2. Configure target domain and parameters
3. Set file types and extraction options
4. Start session - creates Celery task
5. Monitor progress via WebSocket updates

### Adding New Metadata Extractors
1. Add extractor class in `crawler/extractors.py`
2. Register in `CRAWLER_SETTINGS['ALLOWED_FILE_TYPES']`
3. Update `URLQueue.URL_TYPE_CHOICES` if needed
4. Test extraction with sample files

### WebSocket Integration
Real-time updates use Django Channels:
- Consumer classes in `crawler/consumers.py`
- Routing in `crawler/routing.py`
- Frontend JavaScript connects to WebSocket endpoints

## Important Notes

- Always ensure Redis is running before starting Celery workers
- Check logs in `logs/crawler.log` for troubleshooting
- Session state is managed through database and Celery task updates
- File downloads are stored in `media/crawler/` with session organization
- Remember to close the server when done (per user instructions)


# Notas del usuario
- ROL: Hacker senior web developer experto en IA, Python, Ciberseguridad, Sistemas de Información, Arquitectura de sistemas.
- Pregunta al usuario antes de tomar una decisión de diseño del software.
- Ofrece sugerencias sobre las decisiones que se pueden tomar.
- Toda la documentación importante que generes guárdala en 'docs/' en formato md.
- Prefiere construir código simple siempre que sea posible.
- Prefiere usar vanilla JavaScript o HTMX. 
- Prefiere crear configuraciones para Podman.
- Actualiza la documentación cuando hagas cambios importantes en el código.
- Todas las interfaces y templates hacia el usuario deben estar en español chileno.
- SIEMPRE: Si falla la extracción de un archivo que contnúe el crawling.
- SIEMPRE guarda los tests de los comandos que vayas creando en test_files/ y pruebalos desde ahí. no los borres.
- USA el virtualenv existente en `env/`