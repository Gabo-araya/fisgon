# Documentación del Formulario de Nueva Sesión de Crawler

## Análisis Completo del Formulario `/crawler/sesiones/nuevo/`

### Funcionalidad General
El formulario permite crear una nueva sesión de crawling con configuraciones personalizadas para la extracción de metadatos web.

## Estructura del Formulario

### 1. Información Básica
- **Nombre de la sesión** (`name`)
  - Campo obligatorio (*)
  - Input tipo texto
  - Placeholder: "Ej: Crawling de documentos de example.com"
  - Validación: Requerido

- **URL objetivo** (`target_url`) 
  - Campo obligatorio (*)
  - Input tipo URL
  - Placeholder: "https://example.com"
  - Validación en tiempo real con JavaScript
  - Indicadores visuales: ✓ URL válida / ✗ URL no válida
  - Validación backend: debe ser HTTP/HTTPS válido

### 2. Parámetros de Crawling

#### Fila 1:
- **Profundidad máxima** (`max_depth`)
  - Tipo: Number input
  - Rango: 1-10 niveles
  - Valor por defecto: 3
  - Actualización en tiempo real del valor mostrado

- **Límite de velocidad** (`rate_limit`)
  - Tipo: Number input
  - Rango: 0.1-10.0 req/seg
  - Step: 0.1
  - Valor por defecto: 1.0
  - Actualización en tiempo real del valor mostrado

- **Máximo de páginas** (`max_pages`)
  - Tipo: Number input
  - Mínimo: 0 (sin límite)
  - Placeholder: "0 = Sin límite"
  - Valor por defecto: 0

#### Fila 2:
- **Tamaño máximo de archivo** (`max_file_size`)
  - Tipo: Number input con unidad "bytes"
  - Rango: 1MB - 100MB (1048576 - 104857600 bytes)
  - Step: 1MB (1048576)
  - Valor por defecto: 50MB (52428800)
  - Conversión automática a formato legible (MB/KB)
  - Input group con sufijo "bytes"

### 3. Tipos de Archivo a Buscar
- **Layout**: Grid responsivo con auto-fit y minimo 200px por columna
- **Tipos disponibles**:
  - Documentos: PDF, Word (.doc/.docx), Excel (.xls/.xlsx), PowerPoint (.ppt/.pptx)
  - OpenDocument: Text (.odt), Spreadsheet (.ods), Presentation (.odp)
  - Imágenes: JPEG (.jpg/.jpeg), PNG, GIF, TIFF
  - Audio/Video: MP3, MP4
  - Datos: XML, JSON
- **Controles**:
  - Botón "Seleccionar todos" (btn-outline-primary)
  - Botón "Limpiar" (btn-outline-secondary)
  - CheckboxSelectMultiple widget
  - Validación: Al menos un tipo debe ser seleccionado
- **Valores por defecto**: PDF, Word, Excel, PowerPoint seleccionados

### 4. Opciones Avanzadas
Tres switches tipo toggle:

- **Respetar robots.txt** (`respect_robots_txt`)
  - Form switch
  - Por defecto: activado
  
- **Seguir redirecciones** (`follow_redirects`)
  - Form switch
  - Por defecto: activado

- **Extraer metadatos** (`extract_metadata`)
  - Form switch
  - Por defecto: activado

## Panel Lateral

### Vista Previa
Card con resumen dinámico que se actualiza en tiempo real:
- Dominio extraído de la URL
- Profundidad en niveles
- Velocidad en req/seg
- Límite de páginas
- Tamaño máximo en formato legible
- Cantidad de tipos de archivo seleccionados

### Acciones
Tres botones principales:
1. **"Guardar e Iniciar Crawling"** (btn-primary)
   - Icono: bi-rocket
   - Value: "save_and_start"
2. **"Solo Guardar"** (btn-success)
   - Icono: bi-save
   - Value: "save"
3. **"Cancelar"** (btn-outline-secondary)
   - Icono: bi-x-circle
   - Redirige a lista de sesiones

### Ayuda Rápida
Accordion con 3 secciones colapsables:
1. "¿Qué es la profundidad?" - Explicación de niveles de crawling
2. "¿Qué es rate limiting?" - Explicación de límites de velocidad
3. "¿Qué es robots.txt?" - Explicación de políticas de rastreo

## Objetos Ornamentales y Elementos Visuales

### Iconografía Bootstrap Icons
- **Información Básica**: `bi bi-info-circle`
- **Parámetros de Crawling**: `bi bi-gear`
- **Tipos de Archivo**: `bi bi-file-earmark`
- **Opciones Avanzadas**: `bi bi-toggles`
- **Botón Principal**: `bi bi-plus-circle` (en pagetitle)
- **Acciones**: `bi bi-rocket`, `bi bi-save`, `bi bi-x-circle`

### Esquemas de Color
- **Color primario**: `#4154f1` (azul)
- **Bordes activos**: `border-left: 4px solid #4154f1`
- **Estados válidos**: `#198754` (verde)
- **Estados inválidos**: `#dc3545` (rojo)
- **Texto secundario**: `#6c757d` (gris)
- **Fondos hover**: `#f8f9fa` (gris muy claro)

### Elementos Decorativos
- **Form sections**: Borde izquierdo coloreado con padding
- **File type items**: Cajas con bordes redondeados y hover effects
- **Config cards**: Sombra suave en hover
- **Vista previa**: Fondo gris claro con bordes redondeados
- **Range values**: Texto en negrita con color primario
- **Help text**: Texto pequeño en color secundario

### Efectos y Transiciones
- **Hover en file-type-items**: Cambio de fondo
- **Input checked**: Cambio de color y peso de fuente
- **Config cards**: Box-shadow en hover
- **Transiciones CSS**: `transition: all 0.2s`

### Breadcrumb Navigation
- Inicio → Crawler → Nueva Sesión de Crawling
- Enlaces funcionales con navegación

### JavaScript Interactivo
- Validación de URL en tiempo real
- Actualización de vista previa dinámicamente
- Contadores de archivos seleccionados
- Conversión automática de bytes a formato legible
- Validación antes de envío del formulario

## Características de UX/UI
- **Responsive**: Grid adaptable y columnas responsivas
- **Feedback visual**: Indicadores de estado en tiempo real
- **Ayuda contextual**: Help texts y accordion de ayuda
- **Validación progresiva**: Sin necesidad de enviar para ver errores
- **Vista previa**: Resumen en tiempo real de configuración
- **Accesibilidad**: Labels asociados y estructura semántica

## Validaciones Implementadas

### Frontend (JavaScript)
- Validación de formato URL
- Verificación de al menos un tipo de archivo seleccionado
- Actualización de vista previa en tiempo real

### Backend (Django Forms)
- URL válida con protocolo HTTP/HTTPS
- Profundidad entre 1-10 niveles
- Rate limit entre 0.1-10.0 req/seg
- Páginas >= 0
- Tamaño archivo entre 1KB-100MB
- Extracción automática del dominio de la URL