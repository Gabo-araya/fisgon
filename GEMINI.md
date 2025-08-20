# Project Overview

This project, named "Fisgón," is a Django-based web crawler application designed for metadata extraction and security analysis. The system discovers and analyzes files from target domains, extracting metadata from documents (PDFs, Office files, images) to identify potential security exposures like embedded author information, software versions, and GPS coordinates.

## Core Architecture

### Django Apps Structure
- **`core/`**: Main Django project configuration with Celery setup for async tasks
- **`crawler/`**: Core crawling functionality with models, tasks, and metadata extraction
- **`panel/`**: User management and authentication with role-based permissions

### Key Models (`crawler/models.py`)
- **`CrawlSession`**: Main crawling sessions with configuration and status tracking
- **`URLQueue`**: Queue of discovered URLs with processing status
- **`CrawlResult`**: Extracted files and metadata storage  
- **`CrawlLog`**: Event logging for crawling sessions

### Asynchronous Processing
- Uses **Celery** with **Redis** backend for distributed task processing
- Main crawling tasks in `crawler/tasks.py`
- WebSocket support via **Django Channels** for real-time updates

### User Role System
The application implements role-based access control with three user types:
- **`admin`**: Full system access
- **`crawler`**: Can create and manage crawling sessions
- **`viewer`**: Read-only access to results

## Development Commands

### Django Management
- **Start development server**: `python manage.py runserver` or `python manage.py runserver 8000`
- **Create migrations**: `python manage.py makemigrations`
- **Apply migrations**: `python manage.py migrate`
- **Create superuser**: `python manage.py createsuperuser`
- **Collect static files**: `python manage.py collectstatic --noinput`
- **Django shell**: `python manage.py shell`

### Celery and Redis
- **Start Redis server**: `redis-server`
- **Start Celery worker**: `celery -A core worker --loglevel=info`
- **Start Celery beat scheduler**: `celery -A core beat --loglevel=info`
- **Monitor tasks with Flower**: `celery -A core flower`
- **Test Redis connection**: Run `python core/check_redis.py`

### User Management Commands
```python
# Create groups and test users via Django shell
python manage.py shell

from django.contrib.auth.models import User, Group

# Create user groups
admin_group = Group.objects.create(name='admin')
crawler_group = Group.objects.create(name='crawler')
viewer_group = Group.objects.create(name='viewer')

# Create test users
crawler_user = User.objects.create_user(
    username='crawler',
    email='crawler@example.com', 
    password='asdf.1234'
)
crawler_user.groups.add(crawler_group)
```

## Environment Configuration

Create a `.env` file with:
```
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CRAWLER_USER_AGENT=FisgonCrawler/1.0
CRAWLER_MAX_DEPTH=5
CRAWLER_RATE_LIMIT=1.0
```

## Key Dependencies and Features

### Metadata Extraction (`crawler/extractors.py`)
- **PDFs**: PyPDF2 for document metadata (author, creation dates, software)
- **Images**: Pillow + ExifRead for EXIF data including GPS coordinates
- **Office Documents**: python-docx, openpyxl for embedded metadata
- **Audio/Video**: Mutagen for multimedia file metadata

### Crawling Configuration (`core/settings.py`)
```python
CRAWLER_SETTINGS = {
    'DEFAULT_RATE_LIMIT': 1.0,  # requests per second
    'MAX_DEPTH': 5,
    'MAX_PAGES': 1000, 
    'MAX_FILE_SIZE': 50 * 1024 * 1024,  # 50MB
    'ALLOWED_FILE_TYPES': ['pdf', 'doc', 'docx', 'xls', 'xlsx', ...]
}
```

### Authentication
- Uses **Django Allauth** for user authentication
- Custom role-based decorators in `panel/decorators.py`
- Email-based authentication (ACCOUNT_AUTHENTICATION_METHOD = 'email')

## Database Schema

The application uses SQLite by default but supports PostgreSQL. Key relationships:
- `CrawlSession` (1) → `URLQueue` (many) → `CrawlResult` (many)
- Sessions belong to Users and track crawling progress
- URLs maintain parent-child relationships for site mapping
- Results store extracted metadata as JSON fields

## WebSocket Integration

Real-time updates for crawling progress via Django Channels:
- Session status updates
- URL discovery notifications  
- Metadata extraction progress
- Error reporting

## Security Considerations

- Rate limiting to prevent aggressive crawling
- Robots.txt respect (configurable)
- File size limits to prevent resource exhaustion
- Input validation for URLs and domains
- Role-based access controls throughout application

## Testing Access

Default test accounts:
- Admin: `admin4` / `asdf.1234`
- Crawler: `crawler` / `asdf.1234`  
- Viewer: `viewer` / `asdf.1234`

Django admin interface: http://localhost:8000/admin/