# Plan de Implementación: Vista Detalle de Archivo con Metadatos y Contenido Completo

## Resumen Ejecutivo

Implementar una nueva página de detalle para archivos crawleados que muestre metadatos extraídos y contenido completo. Esta vista será accesible desde la página de URLs de sesión (`http://localhost:8000/crawler/sesiones/21/urls/`) mediante un enlace directo por archivo.

## Análisis del Estado Actual

### URL de Referencia Actual
- **Página actual**: `http://localhost:8000/crawler/sesiones/21/urls/`
- **Template**: `crawler/templates/crawler/session_urls.html`
- **Vista**: `views.session_urls`
- **Datos mostrados**: Lista de URLs con estado, tipo, HTTP status, tamaño, metadatos (sí/no)

### Estructura de Datos Disponibles

#### Modelo URLQueue
```python
class URLQueue(models.Model):
    session = models.ForeignKey(CrawlSession)
    url = models.URLField(max_length=2048)
    url_type = models.CharField(max_length=10)
    status = models.CharField(max_length=20)
    has_metadata = models.BooleanField(default=False)
    # ... otros campos
```

#### Modelo CrawlResult
```python
class CrawlResult(models.Model):
    session = models.ForeignKey(CrawlSession)
    url_queue_item = models.ForeignKey(URLQueue)
    metadata = models.JSONField(default=dict)          # Metadatos extraídos
    full_content = models.TextField(blank=True)        # ✅ CONTENIDO COMPLETO
    content_length = models.IntegerField(default=0)    # ✅ Longitud contenido
    content_extracted_at = models.DateTimeField()      # ✅ Fecha extracción
    # ... otros campos
```

### URLs Existentes Relacionadas
```python
# Ya existe en urls.py:
path('archivo/<int:result_id>/metadatos/', views.file_metadata_detail, name='file_metadata_detail'),
```

## Opciones de Implementación

### **Opción A: Enlace Directo desde Columna de Metadatos** ⭐ **RECOMENDADA**

#### Descripción
Agregar enlace en la columna "Metadatos" de la tabla existente que lleve a una página de detalle completa.

#### Ventajas
- ✅ **Mínimo impacto**: Solo modifica template existente
- ✅ **UX intuitiva**: Columna "Metadatos" sugiere función
- ✅ **Escalable**: Funciona para cualquier número de archivos
- ✅ **URL existente**: Reutiliza `file_metadata_detail`

#### Implementación
```html
<!-- En session_urls.html, línea ~302-308 -->
<td>
    {% if url_item.has_metadata %}
        {% if url_item.results.first %}
            <a href="{% url 'crawler:file_metadata_detail' url_item.results.first.id %}" 
               class="btn btn-sm btn-outline-primary" title="Ver metadatos y contenido">
                <i class="bi bi-file-text"></i>
            </a>
        {% else %}
            <i class="bi bi-check-circle text-success" title="Metadatos disponibles"></i>
        {% endif %}
    {% else %}
        <i class="bi bi-dash-circle text-muted" title="Sin metadatos"></i>
    {% endif %}
</td>
```

### **Opción B: Nueva Columna "Acciones"**

#### Descripción
Agregar nueva columna con botones de acción (Ver, Descargar, Analizar).

#### Ventajas
- ✅ **Más acciones**: Espacio para múltiples funciones
- ✅ **Claro propósito**: Columna dedicada a acciones
- ✅ **Extensible**: Fácil agregar más botones

#### Desventajas
- ❌ **Más ancho**: Requiere más espacio horizontal
- ❌ **Complejidad**: Más código y lógica condicional

### **Opción C: Modal en la Misma Página**

#### Descripción
Mostrar metadatos y contenido en modal popup sin cambiar página.

#### Ventajas
- ✅ **Contexto preservado**: No sale de la página de URLs
- ✅ **Rápido**: No hay navegación

#### Desventajas
- ❌ **Espacio limitado**: Modal pequeño para contenido largo
- ❌ **No shareable**: URL no guarda estado del modal

### **Opción D: Expandir Fila (Accordion)**

#### Descripción
Hacer click en fila para expandir y mostrar detalles inline.

#### Desventajas
- ❌ **Complejo**: Mucho JavaScript y lógica
- ❌ **Performance**: Cargar todos los datos desde inicio

## Diseño Detallado de la Solución (Opción A)

### Paso 1: Modificar Template session_urls.html

#### 1.1 Actualizar Columna de Metadatos
```html
<!-- Cambiar header de columna -->
<th style="width: 6%;">Metadatos</th>

<!-- Cambiar contenido de celda -->
<td>
    {% if url_item.has_metadata and url_item.results.first %}
        <a href="{% url 'crawler:file_metadata_detail' url_item.results.first.id %}" 
           class="btn btn-sm btn-outline-primary" 
           title="Ver metadatos y contenido completo"
           target="_blank">
            <i class="bi bi-file-text"></i>
            <span class="d-none d-lg-inline ms-1">Ver</span>
        </a>
    {% elif url_item.has_metadata %}
        <i class="bi bi-check-circle text-success" title="Metadatos disponibles sin archivo"></i>
    {% else %}
        <i class="bi bi-dash-circle text-muted" title="Sin metadatos"></i>
    {% endif %}
</td>
```

#### 1.2 Agregar Tooltip Explicativo
```html
<!-- En la sección de filtros, agregar ayuda -->
<div class="alert alert-info alert-dismissible fade show" role="alert">
    <i class="bi bi-info-circle"></i>
    <strong>Nuevo:</strong> Haz click en el botón <i class="bi bi-file-text"></i> "Ver" para acceder a metadatos y contenido completo extraído.
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
</div>
```

### Paso 2: Mejorar Vista file_metadata_detail

#### 2.1 Verificar Vista Existente
```python
# En views.py - verificar que exista
def file_metadata_detail(request, result_id):
    try:
        result = CrawlResult.objects.get(id=result_id)
        # Verificar permisos del usuario
        if result.session.user != request.user:
            return HttpResponseForbidden("No tienes acceso a este resultado")
        
        context = {
            'result': result,
            'metadata': result.metadata,
            'full_content': result.full_content,
            'content_length': result.content_length,
            'has_content': bool(result.full_content),
            'session': result.session,
            'url_item': result.url_queue_item,
        }
        return render(request, 'crawler/file_detail.html', context)
    except CrawlResult.DoesNotExist:
        raise Http404("Resultado no encontrado")
```

#### 2.2 Crear/Mejorar Template file_detail.html
```html
<!-- crawler/templates/crawler/file_detail.html -->
{% extends "panel/base_admin.html" %}
{% load static %}

{% block title %}Detalle de Archivo - {{ result.file_name|default:"Archivo" }}{% endblock %}

{% block content %}
<main id="main" class="main">
    <div class="pagetitle">
        <h1><i class="bi bi-file-text"></i> Detalle de Archivo</h1>
        <nav>
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="{% url 'crawler:dashboard' %}">Crawler</a></li>
                <li class="breadcrumb-item"><a href="{% url 'crawler:session_detail' session.pk %}">{{ session.name }}</a></li>
                <li class="breadcrumb-item"><a href="{% url 'crawler:session_urls' session.pk %}">URLs</a></li>
                <li class="breadcrumb-item active">Archivo</li>
            </ol>
        </nav>
    </div>

    <section class="section">
        <div class="row">
            <!-- Información General -->
            <div class="col-12 mb-4">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="bi bi-info-circle"></i> Información General
                        </h5>
                        <div class="row">
                            <div class="col-md-6">
                                <table class="table table-sm">
                                    <tr>
                                        <th>URL:</th>
                                        <td>
                                            <a href="{{ url_item.url }}" target="_blank" class="text-break">
                                                {{ url_item.url }}
                                                <i class="bi bi-box-arrow-up-right ms-1"></i>
                                            </a>
                                        </td>
                                    </tr>
                                    <tr>
                                        <th>Nombre de archivo:</th>
                                        <td>{{ result.file_name|default:"No disponible" }}</td>
                                    </tr>
                                    <tr>
                                        <th>Tipo:</th>
                                        <td>
                                            <span class="badge bg-primary">{{ url_item.url_type|upper }}</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <th>Tamaño:</th>
                                        <td>{{ url_item.file_size|filesizeformat|default:"No disponible" }}</td>
                                    </tr>
                                </table>
                            </div>
                            <div class="col-md-6">
                                <table class="table table-sm">
                                    <tr>
                                        <th>Estado HTTP:</th>
                                        <td>
                                            {% if url_item.http_status_code %}
                                                <span class="badge bg-{% if url_item.http_status_code == 200 %}success{% else %}warning{% endif %}">
                                                    {{ url_item.http_status_code }}
                                                </span>
                                            {% else %}
                                                No disponible
                                            {% endif %}
                                        </td>
                                    </tr>
                                    <tr>
                                        <th>Procesado:</th>
                                        <td>{{ result.created_at|date:"d/m/Y H:i:s" }}</td>
                                    </tr>
                                    <tr>
                                        <th>Hash SHA-256:</th>
                                        <td class="font-monospace small">{{ result.file_hash|default:"No disponible" }}</td>
                                    </tr>
                                    <tr>
                                        <th>Profundidad:</th>
                                        <td>
                                            <span class="badge bg-light text-dark">{{ url_item.depth }}</span>
                                        </td>
                                    </tr>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Metadatos Extraídos -->
            <div class="col-12 mb-4">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="bi bi-tags"></i> Metadatos Extraídos
                            <span class="badge bg-info ms-2">{{ metadata|length }} campos</span>
                        </h5>
                        
                        {% if metadata %}
                            <div class="accordion" id="metadataAccordion">
                                {% for section_name, section_data in metadata.items %}
                                <div class="accordion-item">
                                    <h2 class="accordion-header">
                                        <button class="accordion-button collapsed" type="button" 
                                                data-bs-toggle="collapse" data-bs-target="#collapse{{ forloop.counter }}">
                                            <i class="bi bi-folder me-2"></i>
                                            {{ section_name|title }}
                                            {% if section_data|length %}
                                                <span class="badge bg-secondary ms-2">{{ section_data|length }}</span>
                                            {% endif %}
                                        </button>
                                    </h2>
                                    <div id="collapse{{ forloop.counter }}" class="accordion-collapse collapse">
                                        <div class="accordion-body">
                                            <pre class="bg-light p-3 rounded">{{ section_data|pprint }}</pre>
                                        </div>
                                    </div>
                                </div>
                                {% endfor %}
                            </div>
                        {% else %}
                            <div class="alert alert-info">
                                <i class="bi bi-info-circle"></i>
                                No se encontraron metadatos para este archivo.
                            </div>
                        {% endif %}
                    </div>
                </div>
            </div>

            <!-- Contenido Completo -->
            <div class="col-12 mb-4">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="bi bi-file-text"></i> Contenido Completo
                            {% if has_content %}
                                <span class="badge bg-success ms-2">{{ content_length|floatformat:0 }} caracteres</span>
                                {% if result.content_extracted_at %}
                                    <small class="text-muted ms-2">
                                        Extraído: {{ result.content_extracted_at|date:"d/m/Y H:i:s" }}
                                    </small>
                                {% endif %}
                            {% endif %}
                        </h5>
                        
                        {% if has_content %}
                            <!-- Controles de contenido -->
                            <div class="d-flex gap-2 mb-3">
                                <button class="btn btn-sm btn-outline-primary" onclick="toggleContentView()">
                                    <i class="bi bi-eye" id="toggleIcon"></i>
                                    <span id="toggleText">Mostrar contenido</span>
                                </button>
                                <button class="btn btn-sm btn-outline-secondary" onclick="copyContent()">
                                    <i class="bi bi-clipboard"></i> Copiar
                                </button>
                                <button class="btn btn-sm btn-outline-info" onclick="searchInContent()">
                                    <i class="bi bi-search"></i> Buscar
                                </button>
                            </div>
                            
                            <!-- Contenido colapsado por defecto -->
                            <div id="contentContainer" class="d-none">
                                <div class="bg-light p-3 rounded" style="max-height: 500px; overflow-y: auto;">
                                    <pre id="fullContent" class="mb-0 small">{{ full_content }}</pre>
                                </div>
                            </div>
                            
                            <!-- Búsqueda en contenido -->
                            <div id="searchContainer" class="d-none mt-3">
                                <div class="input-group">
                                    <input type="text" class="form-control" id="searchInput" 
                                           placeholder="Buscar en contenido...">
                                    <button class="btn btn-outline-primary" type="button" onclick="performSearch()">
                                        <i class="bi bi-search"></i>
                                    </button>
                                </div>
                                <div id="searchResults" class="mt-2"></div>
                            </div>
                        {% else %}
                            <div class="alert alert-warning">
                                <i class="bi bi-exclamation-triangle"></i>
                                No se extrajo contenido completo para este archivo.
                                <small class="d-block mt-1">
                                    Posibles razones: tipo de archivo no soportado, archivo muy grande, o error en procesamiento.
                                </small>
                            </div>
                        {% endif %}
                    </div>
                </div>
            </div>

            <!-- Acciones -->
            <div class="col-12">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="bi bi-gear"></i> Acciones
                        </h5>
                        <div class="d-flex gap-2">
                            <a href="{% url 'crawler:session_urls' session.pk %}" class="btn btn-secondary">
                                <i class="bi bi-arrow-left"></i> Volver a URLs
                            </a>
                            {% if result.file_path %}
                            <a href="{% url 'crawler:api_result_download' result.id %}" 
                               class="btn btn-primary" target="_blank">
                                <i class="bi bi-download"></i> Descargar archivo original
                            </a>
                            {% endif %}
                            <button class="btn btn-outline-info" onclick="showAnalysisModal()">
                                <i class="bi bi-graph-up"></i> Análisis avanzado
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>
</main>

<!-- Modal de análisis avanzado -->
<div class="modal fade" id="analysisModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">
                    <i class="bi bi-graph-up"></i> Análisis Avanzado
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="row">
                    <div class="col-md-6">
                        <h6>Estadísticas de contenido:</h6>
                        <ul class="list-unstyled">
                            <li><strong>Palabras:</strong> <span id="wordCount">-</span></li>
                            <li><strong>Líneas:</strong> <span id="lineCount">-</span></li>
                            <li><strong>Caracteres sin espacios:</strong> <span id="charCount">-</span></li>
                        </ul>
                    </div>
                    <div class="col-md-6">
                        <h6>Detección de patrones:</h6>
                        <ul class="list-unstyled" id="patternDetection">
                            <!-- Se llena dinámicamente -->
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
// JavaScript para funcionalidad interactiva
let contentVisible = false;
let searchVisible = false;

function toggleContentView() {
    const container = document.getElementById('contentContainer');
    const icon = document.getElementById('toggleIcon');
    const text = document.getElementById('toggleText');
    
    if (contentVisible) {
        container.classList.add('d-none');
        icon.className = 'bi bi-eye';
        text.textContent = 'Mostrar contenido';
        contentVisible = false;
    } else {
        container.classList.remove('d-none');
        icon.className = 'bi bi-eye-slash';
        text.textContent = 'Ocultar contenido';
        contentVisible = true;
    }
}

function copyContent() {
    const content = document.getElementById('fullContent').textContent;
    navigator.clipboard.writeText(content).then(() => {
        // Mostrar toast de confirmación
        showToast('Contenido copiado al portapapeles', 'success');
    });
}

function searchInContent() {
    const container = document.getElementById('searchContainer');
    searchVisible = !searchVisible;
    
    if (searchVisible) {
        container.classList.remove('d-none');
        document.getElementById('searchInput').focus();
    } else {
        container.classList.add('d-none');
    }
}

function performSearch() {
    const query = document.getElementById('searchInput').value;
    const content = document.getElementById('fullContent').textContent;
    const resultsDiv = document.getElementById('searchResults');
    
    if (!query) {
        resultsDiv.innerHTML = '';
        return;
    }
    
    // Buscar coincidencias
    const regex = new RegExp(query, 'gi');
    const matches = content.match(regex);
    
    if (matches) {
        resultsDiv.innerHTML = `
            <div class="alert alert-info">
                <i class="bi bi-search"></i> 
                Encontradas <strong>${matches.length}</strong> coincidencias para "${query}"
            </div>
        `;
        
        // Resaltar en el contenido
        const highlightedContent = content.replace(regex, `<mark>$&</mark>`);
        document.getElementById('fullContent').innerHTML = highlightedContent;
    } else {
        resultsDiv.innerHTML = `
            <div class="alert alert-warning">
                <i class="bi bi-exclamation-triangle"></i> 
                No se encontraron coincidencias para "${query}"
            </div>
        `;
    }
}

function showAnalysisModal() {
    const content = document.getElementById('fullContent')?.textContent || '';
    
    if (content) {
        // Calcular estadísticas
        const words = content.split(/\s+/).filter(w => w.length > 0).length;
        const lines = content.split('\n').length;
        const chars = content.replace(/\s/g, '').length;
        
        document.getElementById('wordCount').textContent = words.toLocaleString();
        document.getElementById('lineCount').textContent = lines.toLocaleString();
        document.getElementById('charCount').textContent = chars.toLocaleString();
        
        // Detectar patrones (ejemplo básico)
        const patterns = [
            { name: 'Emails', pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g },
            { name: 'RUTs chilenos', pattern: /\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b/g },
            { name: 'Teléfonos', pattern: /\b(\+56|56)?\s?[9]\s?\d{4}\s?\d{4}\b/g },
            { name: 'URLs', pattern: /https?:\/\/[^\s]+/g }
        ];
        
        const patternDiv = document.getElementById('patternDetection');
        patternDiv.innerHTML = '';
        
        patterns.forEach(p => {
            const matches = content.match(p.pattern);
            const count = matches ? matches.length : 0;
            const color = count > 0 ? 'text-danger' : 'text-muted';
            patternDiv.innerHTML += `
                <li class="${color}">
                    <strong>${p.name}:</strong> ${count}
                </li>
            `;
        });
    }
    
    new bootstrap.Modal(document.getElementById('analysisModal')).show();
}

function showToast(message, type = 'info') {
    // Implementar toast notification
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999;';
    toast.innerHTML = `
        <i class="bi bi-check-circle"></i> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(toast);
    
    setTimeout(() => toast.remove(), 3000);
}
</script>
{% endblock %}
```

### Paso 3: Verificar URLs y Vistas

#### 3.1 Verificar URL Existente
```python
# Ya existe en urls.py:
path('archivo/<int:result_id>/metadatos/', views.file_metadata_detail, name='file_metadata_detail'),
```

#### 3.2 Asegurar Relación en Queries
```python
# En views.py para session_urls - asegurar que se incluyan results
def session_urls(request, pk):
    session = get_object_or_404(CrawlSession, pk=pk, user=request.user)
    
    urls = URLQueue.objects.filter(session=session).select_related(
        'session'
    ).prefetch_related(
        'results'  # ✅ IMPORTANTE: Incluir results para acceder a CrawlResult
    ).order_by('-discovered_at')
    
    # ... resto de la vista
```

## Plan de Implementación por Fases

### **Fase 1: Modificación Básica (30 minutos)**
- [ ] Modificar template `session_urls.html`
- [ ] Cambiar columna "Metadatos" para incluir enlace
- [ ] Probar navegación básica

### **Fase 2: Vista de Detalle (60 minutos)**
- [ ] Crear/mejorar template `file_detail.html`
- [ ] Implementar secciones de información general
- [ ] Mostrar metadatos en formato legible
- [ ] Mostrar contenido completo colapsado

### **Fase 3: Funcionalidad Interactiva (45 minutos)**
- [ ] JavaScript para mostrar/ocultar contenido
- [ ] Función de búsqueda en contenido
- [ ] Copiar contenido al portapapeles
- [ ] Modal de análisis avanzado

### **Fase 4: Pulimiento y Testing (30 minutos)**
- [ ] CSS y estilos responsivos
- [ ] Pruebas con diferentes tipos de archivo
- [ ] Validar permisos de usuario
- [ ] Breadcrumb y navegación

## Alternativas de Integración

### **Integración A: Enlace Directo** ⭐ **RECOMENDADA**
```html
<td>
    {% if url_item.has_metadata and url_item.results.first %}
        <a href="{% url 'crawler:file_metadata_detail' url_item.results.first.id %}">
            <i class="bi bi-file-text"></i> Ver
        </a>
    {% endif %}
</td>
```

### **Integración B: Dropdown de Acciones**
```html
<td>
    {% if url_item.has_metadata %}
        <div class="dropdown">
            <button class="btn btn-sm btn-outline-primary dropdown-toggle">
                Acciones
            </button>
            <ul class="dropdown-menu">
                <li><a class="dropdown-item" href="...">Ver metadatos</a></li>
                <li><a class="dropdown-item" href="...">Descargar</a></li>
                <li><a class="dropdown-item" href="...">Analizar</a></li>
            </ul>
        </div>
    {% endif %}
</td>
```

### **Integración C: Iconos Múltiples**
```html
<td>
    {% if url_item.has_metadata %}
        <a href="..." title="Ver metadatos"><i class="bi bi-file-text"></i></a>
        <a href="..." title="Descargar"><i class="bi bi-download"></i></a>
        <a href="..." title="Análisis"><i class="bi bi-graph-up"></i></a>
    {% endif %}
</td>
```

## Casos de Uso Cubiertos

### **Para Analistas de Seguridad:**
1. **Revisión de metadatos**: Ver toda la información extraída
2. **Análisis de contenido**: Buscar patrones sensibles en texto completo
3. **Investigación forense**: Acceso completo a datos del archivo

### **Para Administradores:**
1. **Validación de extracción**: Verificar que el crawler funciona
2. **Audit trail**: Ver cuándo y cómo se procesó cada archivo
3. **Troubleshooting**: Identificar archivos problemáticos

### **Para Usuarios Generales:**
1. **Exploración de datos**: Navegar resultados fácilmente
2. **Export de información**: Copiar contenido relevante
3. **Comprensión de resultados**: Ver qué se encontró

## Métricas de Éxito

### **Usabilidad:**
- ✅ 1-2 clicks desde lista de URLs a detalle completo
- ✅ Información organizada y fácil de leer
- ✅ Funcionalidad de búsqueda operativa

### **Funcionalidad:**
- ✅ Metadatos mostrados correctamente
- ✅ Contenido completo accesible
- ✅ Análisis básico de patrones

### **Performance:**
- ✅ Carga de página <2 segundos
- ✅ Búsqueda en contenido <1 segundo
- ✅ Responsive en móviles

## Riesgos y Mitigaciones

### **Riesgo 1: Contenido Muy Grande**
- **Problema**: Archivos con contenido de 1M caracteres
- **Mitigación**: Mostrar contenido colapsado por defecto, con scroll

### **Riesgo 2: Información Sensible Expuesta**
- **Problema**: Mostrar datos confidenciales en pantalla
- **Mitigación**: Verificar permisos de usuario, marcar contenido sensible

### **Riesgo 3: Performance en Móviles**
- **Problema**: Página pesada para dispositivos móviles
- **Mitigación**: Lazy loading, contenido colapsado, CSS responsive

---

*Plan de implementación - 2025-08-20*  
*Tiempo estimado total: 2.5-3 horas*  
*Prioridad: ALTA - Mejora significativa de UX*