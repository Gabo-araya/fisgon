# Plan de Implementación: Extracción Completa de Datos de Archivos XLS y XLSX

## Resumen Ejecutivo

Implementar la extracción de **contenido completo** de archivos Excel (XLS y XLSX) para capturar datos de celdas, fórmulas, nombres de rangos y contenido sensible. Actualmente solo se extraen metadatos y estructura de hojas, perdiendo información valiosa para análisis de seguridad.

## Análisis del Estado Actual

### Limitaciones Actuales

#### XLSX (Excel Moderno)
```python
# Estado actual en _extract_xlsx_metadata()
sheets_info = []
for sheet_name in workbook.sheetnames:
    sheet = workbook[sheet_name]
    sheets_info.append({
        'name': sheet_name,           # ✅ Nombre de hoja
        'max_row': sheet.max_row,     # ✅ Número de filas
        'max_column': sheet.max_column # ✅ Número de columnas
    })
# ❌ FALTANTE: Contenido de las celdas
```

#### XLS (Excel Legacy)
```python
# Estado actual en _extract_xls_metadata()
for sheet_name in workbook.sheet_names():
    sheet = workbook.sheet_by_name(sheet_name)
    sheets_info.append({
        'name': sheet_name,
        'nrows': sheet.nrows,        # ✅ Número de filas
        'ncols': sheet.ncols         # ✅ Número de columnas
    })
# ❌ FALTANTE: Contenido de las celdas
```

### Información Perdida Actualmente

#### Datos Críticos No Extraídos
- **Contenido de celdas**: Texto, números, fechas
- **Fórmulas**: Cálculos y referencias
- **Nombres de rangos**: Pueden revelar propósito (ej: "SALARIOS", "CLIENTES")
- **Comentarios de celdas**: Notas explicativas
- **Validación de datos**: Restricciones y listas
- **Formato condicional**: Reglas de negocio

#### Casos de Uso de Seguridad Perdidos
- **Detección de información personal**: RUTs, emails, teléfonos en celdas
- **Información financiera**: Números de cuenta, montos, salarios
- **Listas de usuarios/clientes**: Bases de datos exportadas
- **Credenciales**: Contraseñas en hojas "ocultas"
- **Configuraciones**: Parámetros de sistema en Excel

## Objetivos de la Implementación

### 🎯 Objetivo Principal
Extraer contenido completo de archivos Excel para análisis de seguridad, manteniendo límites de performance y almacenamiento.

### 📊 Métricas de Éxito
- **Cobertura**: >90% de archivos XLS/XLSX procesados exitosamente
- **Performance**: <10 segundos promedio por archivo
- **Contenido**: Capturar primeras 1000 celdas con datos por hoja
- **Detección**: Identificar información sensible en contenido de celdas

## Diseño de la Solución

### Arquitectura Propuesta

#### 1. Nuevos Métodos de Extracción
```python
class OfficeExtractor(MetadataExtractor):
    def extract_full_xlsx_content(self) -> str:
        '''Extrae contenido completo de archivo XLSX'''
    
    def extract_full_xls_content(self) -> str:
        '''Extrae contenido completo de archivo XLS legacy'''
    
    def _extract_sheet_content(self, sheet, sheet_name: str, format_type: str) -> str:
        '''Extrae contenido de una hoja específica'''
    
    def _extract_cell_content(self, cell, row: int, col: int) -> dict:
        '''Extrae contenido de una celda específica'''
```

#### 2. Estructura de Datos de Salida
```python
# Contenido completo extraído
{
    "sheets_content": [
        {
            "sheet_name": "Datos",
            "content_summary": {
                "total_cells_with_data": 150,
                "cells_extracted": 100,  # Limitado por configuración
                "has_formulas": True,
                "has_comments": False
            },
            "cell_data": [
                {
                    "position": "A1",
                    "value": "Nombre Cliente",
                    "type": "string",
                    "formula": None
                },
                {
                    "position": "B1", 
                    "value": "12.345.678-9",
                    "type": "string",
                    "contains_rut": True
                },
                {
                    "position": "C1",
                    "value": 1500000,
                    "type": "number",
                    "formula": "=SUM(D1:D10)"
                }
            ],
            "text_content": "Nombre Cliente | RUT | Monto\nJuan Pérez | 12.345.678-9 | 1500000\n...",
            "sensitive_data_detected": {
                "ruts": ["12.345.678-9"],
                "emails": ["admin@empresa.cl"],
                "potential_financial": [1500000, 2500000]
            }
        }
    ]
}
```

## Implementación Detallada

### Fase 1: Métodos de Extracción XLSX

#### 1.1 Método Principal
```python
def extract_full_xlsx_content(self) -> str:
    '''Extrae contenido completo de archivo XLSX'''
    if not OPENPYXL_AVAILABLE:
        logger.warning("openpyxl no disponible para extracción de contenido")
        return ""
    
    try:
        from django.conf import settings
        
        # Configuración de límites
        config = getattr(settings, 'CONTENT_EXTRACTION_SETTINGS', {})
        max_cells_per_sheet = config.get('MAX_EXCEL_CELLS_PER_SHEET', 1000)
        max_sheets = config.get('MAX_EXCEL_SHEETS', 10)
        
        workbook = load_workbook(self.file_path, data_only=True)
        sheets_content = []
        
        for i, sheet_name in enumerate(workbook.sheetnames[:max_sheets]):
            sheet = workbook[sheet_name]
            sheet_content = self._extract_xlsx_sheet_content(
                sheet, sheet_name, max_cells_per_sheet
            )
            if sheet_content:
                sheets_content.append(sheet_content)
        
        # Convertir a texto plano para almacenamiento
        full_content = self._format_excel_content_as_text(sheets_content)
        
        logger.info(f"XLSX contenido extraído: {len(full_content)} caracteres de {len(sheets_content)} hojas")
        return full_content
        
    except Exception as e:
        logger.error(f"Error extrayendo contenido completo XLSX: {str(e)}")
        return ""
```

#### 1.2 Extracción por Hoja
```python
def _extract_xlsx_sheet_content(self, sheet, sheet_name: str, max_cells: int) -> str:
    '''Extrae contenido de una hoja XLSX específica'''
    try:
        content_lines = [f"=== HOJA: {sheet_name} ==="]
        cells_processed = 0
        
        # Obtener rango de datos con contenido
        if sheet.max_row == 1 and sheet.max_column == 1:
            # Hoja vacía
            content_lines.append("(Hoja vacía)")
            return "\n".join(content_lines)
        
        # Procesar filas con datos
        for row in sheet.iter_rows(min_row=1, max_row=min(sheet.max_row, 100), 
                                  min_col=1, max_col=min(sheet.max_column, 50)):
            if cells_processed >= max_cells:
                content_lines.append(f"... (limitado a {max_cells} celdas)")
                break
                
            row_data = []
            has_data = False
            
            for cell in row:
                if cell.value is not None:
                    has_data = True
                    cell_content = self._format_cell_value(cell)
                    row_data.append(cell_content)
                    cells_processed += 1
                else:
                    row_data.append("")
            
            if has_data:
                content_lines.append(" | ".join(row_data))
        
        # Detectar nombres de rangos definidos
        if hasattr(sheet.parent, 'defined_names'):
            range_names = []
            for defined_name in sheet.parent.defined_names:
                if defined_name.name and sheet_name in str(defined_name.value):
                    range_names.append(defined_name.name)
            
            if range_names:
                content_lines.append(f"=== RANGOS DEFINIDOS ===")
                content_lines.append(", ".join(range_names))
        
        return "\n".join(content_lines)
        
    except Exception as e:
        logger.warning(f"Error extrayendo hoja {sheet_name}: {str(e)}")
        return f"=== HOJA: {sheet_name} === (Error en extracción)"
```

#### 1.3 Formateo de Celdas
```python
def _format_cell_value(self, cell) -> str:
    '''Formatea el valor de una celda para extracción de texto'''
    try:
        if cell.value is None:
            return ""
        
        # Detectar fórmulas
        if hasattr(cell, 'formula') and cell.formula:
            return f"{cell.value} [={cell.formula}]"
        
        # Formatear según tipo
        if isinstance(cell.value, (int, float)):
            return str(cell.value)
        elif isinstance(cell.value, str):
            # Detectar patrones sensibles en contenido
            content = cell.value.strip()
            if self._contains_sensitive_pattern(content):
                return f"[SENSITIVE]{content}"
            return content
        else:
            return str(cell.value)
            
    except Exception as e:
        return f"[ERROR:{str(e)}]"

def _contains_sensitive_pattern(self, text: str) -> bool:
    '''Detecta patrones sensibles en texto de celda'''
    import re
    
    sensitive_patterns = [
        r'\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b',  # RUT chileno
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Tarjeta/cuenta
        r'\bpasword\b|\bpasswd\b|\bclave\b',  # Palabras clave sensibles
    ]
    
    for pattern in sensitive_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False
```

### Fase 2: Métodos de Extracción XLS Legacy

#### 2.1 Método Principal XLS
```python
def extract_full_xls_content(self) -> str:
    '''Extrae contenido completo de archivo XLS legacy'''
    try:
        # Intentar con xlrd primero
        try:
            import xlrd
            return self._extract_xls_with_xlrd()
        except ImportError:
            logger.warning("xlrd no disponible")
        
        # Fallback: intentar con openpyxl
        if OPENPYXL_AVAILABLE:
            logger.info("Intentando XLS con openpyxl")
            return self.extract_full_xlsx_content()  # Reutilizar método XLSX
        
        logger.warning("No hay librerías disponibles para extraer contenido XLS")
        return ""
        
    except Exception as e:
        logger.error(f"Error extrayendo contenido completo XLS: {str(e)}")
        return ""

def _extract_xls_with_xlrd(self) -> str:
    '''Extrae contenido XLS usando xlrd'''
    import xlrd
    from django.conf import settings
    
    config = getattr(settings, 'CONTENT_EXTRACTION_SETTINGS', {})
    max_cells_per_sheet = config.get('MAX_EXCEL_CELLS_PER_SHEET', 1000)
    max_sheets = config.get('MAX_EXCEL_SHEETS', 10)
    
    workbook = xlrd.open_workbook(self.file_path)
    sheets_content = []
    
    for i, sheet_name in enumerate(workbook.sheet_names()[:max_sheets]):
        sheet = workbook.sheet_by_name(sheet_name)
        sheet_content = self._extract_xls_sheet_content(sheet, sheet_name, max_cells_per_sheet)
        if sheet_content:
            sheets_content.append(sheet_content)
    
    full_content = "\n\n".join(sheets_content)
    logger.info(f"XLS contenido extraído: {len(full_content)} caracteres")
    return full_content

def _extract_xls_sheet_content(self, sheet, sheet_name: str, max_cells: int) -> str:
    '''Extrae contenido de una hoja XLS específica'''
    try:
        content_lines = [f"=== HOJA: {sheet_name} ==="]
        cells_processed = 0
        
        if sheet.nrows == 0 or sheet.ncols == 0:
            content_lines.append("(Hoja vacía)")
            return "\n".join(content_lines)
        
        # Procesar filas limitadas
        max_rows = min(sheet.nrows, 100)
        max_cols = min(sheet.ncols, 50)
        
        for row_idx in range(max_rows):
            if cells_processed >= max_cells:
                content_lines.append(f"... (limitado a {max_cells} celdas)")
                break
                
            row_data = []
            has_data = False
            
            for col_idx in range(max_cols):
                cell_value = sheet.cell_value(row_idx, col_idx)
                if cell_value is not None and cell_value != "":
                    has_data = True
                    formatted_value = self._format_xls_cell_value(cell_value)
                    row_data.append(formatted_value)
                    cells_processed += 1
                else:
                    row_data.append("")
            
            if has_data:
                content_lines.append(" | ".join(row_data))
        
        return "\n".join(content_lines)
        
    except Exception as e:
        logger.warning(f"Error extrayendo hoja XLS {sheet_name}: {str(e)}")
        return f"=== HOJA: {sheet_name} === (Error en extracción)"

def _format_xls_cell_value(self, cell_value) -> str:
    '''Formatea valor de celda XLS'''
    if isinstance(cell_value, (int, float)):
        return str(cell_value)
    elif isinstance(cell_value, str):
        content = cell_value.strip()
        if self._contains_sensitive_pattern(content):
            return f"[SENSITIVE]{content}"
        return content
    else:
        return str(cell_value)
```

### Fase 3: Integración en Pipeline

#### 3.1 Actualizar Función Principal
```python
# En extractors.py - función extract_full_content_from_file()
def extract_full_content_from_file(file_path: str) -> str:
    '''Extrae contenido completo de un archivo según su tipo'''
    try:
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            extractor = PDFExtractor(file_path)
            return extractor.extract_full_content()
        elif file_extension == '.docx':
            extractor = OfficeExtractor(file_path)
            return extractor.extract_full_docx_content()
        elif file_extension == '.doc':
            extractor = OfficeExtractor(file_path)
            return extractor.extract_full_doc_content()
        elif file_extension == '.odt':
            extractor = OpenOfficeExtractor(file_path)
            return extractor.extract_full_odt_content()
        # NUEVOS: Soporte para Excel
        elif file_extension == '.xlsx':
            extractor = OfficeExtractor(file_path)
            return extractor.extract_full_xlsx_content()
        elif file_extension == '.xls':
            extractor = OfficeExtractor(file_path)
            return extractor.extract_full_xls_content()
        else:
            logger.info(f"Tipo de archivo no soportado para extracción completa: {file_extension}")
            return ""
            
    except Exception as e:
        logger.error(f"Error extrayendo contenido completo de {file_path}: {str(e)}")
        return ""
```

#### 3.2 Actualizar Configuración
```python
# En core/settings.py - CONTENT_EXTRACTION_SETTINGS
CONTENT_EXTRACTION_SETTINGS = {
    'MAX_FILE_SIZE_MB': 50,
    'MAX_CONTENT_CHARS': 1000000,
    'MAX_PDF_PAGES': 500,
    'ENABLE_DOC_EXTRACTION': True,
    'EXTRACTION_TIMEOUT': 60,
    'SUPPORTED_FORMATS': ['pdf', 'docx', 'doc', 'odt', 'xlsx', 'xls'],  # Agregados xlsx, xls
    
    # NUEVOS: Configuración específica para Excel
    'MAX_EXCEL_CELLS_PER_SHEET': 1000,  # Máximo 1000 celdas por hoja
    'MAX_EXCEL_SHEETS': 10,             # Máximo 10 hojas por archivo
    'EXCEL_MAX_ROWS': 100,              # Máximo 100 filas por hoja
    'EXCEL_MAX_COLS': 50,               # Máximo 50 columnas por hoja
    'DETECT_SENSITIVE_DATA': True,      # Activar detección de datos sensibles
}
```

## Consideraciones de Performance

### Límites Propuestos

#### Por Archivo
- **Tamaño máximo**: 50MB (existente)
- **Hojas máximas**: 10 hojas por archivo
- **Timeout**: 60 segundos por archivo

#### Por Hoja
- **Celdas máximas**: 1000 celdas con datos por hoja
- **Filas máximas**: 100 filas por hoja
- **Columnas máximas**: 50 columnas por hoja

#### Contenido Final
- **Caracteres máximos**: 1M caracteres (límite existente)
- **Truncamiento**: Si excede el límite, cortar por hojas completas

### Optimizaciones

#### Lectura Eficiente
```python
# Usar data_only=True para valores calculados
workbook = load_workbook(file_path, data_only=True, read_only=True)

# Iterar solo rangos con datos
for row in sheet.iter_rows(min_row=1, max_row=sheet.max_row, values_only=True):
    # Procesar solo valores, no objetos Cell completos
```

#### Detección Temprana de Hojas Vacías
```python
if sheet.max_row == 1 and sheet.max_column == 1:
    if sheet.cell(1, 1).value is None:
        continue  # Saltar hoja vacía
```

#### Manejo de Memoria
```python
# Procesar hoja por hoja, no cargar todo en memoria
# Usar generadores en lugar de listas grandes
# Cerrar workbook explícitamente después del procesamiento
```

## Casos de Uso de Seguridad

### Información Sensible Detectada

#### Datos Personales
```python
# Patrones a detectar en contenido de celdas
sensitive_patterns = {
    'rut': r'\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b',
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'phone': r'\b(\+56|56)?\s?[9]\s?\d{4}\s?\d{4}\b',
    'card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
    'account': r'\b\d{8,20}\b'
}
```

#### Información Financiera
- Números de cuenta bancaria
- Montos en formato monetario
- Códigos de transacción
- Referencias a sistemas financieros

#### Credenciales y Configuraciones
- Palabras como "password", "clave", "token"
- URLs de sistemas internos
- Nombres de usuario y roles
- Configuraciones de sistemas

### Alertas Automáticas

#### Detección de Alto Riesgo
```python
def analyze_excel_security_risk(content: str, metadata: dict) -> dict:
    risk_indicators = {
        'sensitive_data_count': 0,
        'risk_level': 'LOW',
        'alerts': []
    }
    
    # Detectar patrones sensibles
    for pattern_name, pattern in sensitive_patterns.items():
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            risk_indicators['sensitive_data_count'] += len(matches)
            risk_indicators['alerts'].append(f'{pattern_name}: {len(matches)} encontrados')
    
    # Evaluar riesgo por nombre de hojas
    sheet_names = [sheet['name'] for sheet in metadata.get('sheets_info', [])]
    high_risk_names = ['password', 'clave', 'personal', 'cliente', 'nomina', 'salario']
    
    for sheet_name in sheet_names:
        for risk_name in high_risk_names:
            if risk_name.lower() in sheet_name.lower():
                risk_indicators['alerts'].append(f'Hoja de riesgo: {sheet_name}')
                risk_indicators['sensitive_data_count'] += 10  # Peso alto
    
    # Calcular nivel de riesgo
    if risk_indicators['sensitive_data_count'] > 50:
        risk_indicators['risk_level'] = 'CRITICAL'
    elif risk_indicators['sensitive_data_count'] > 10:
        risk_indicators['risk_level'] = 'HIGH'
    elif risk_indicators['sensitive_data_count'] > 0:
        risk_indicators['risk_level'] = 'MEDIUM'
    
    return risk_indicators
```

## Plan de Implementación

### Fase 1: Desarrollo Base (2-3 horas)
- [ ] Implementar `extract_full_xlsx_content()` en `OfficeExtractor`
- [ ] Implementar `extract_full_xls_content()` en `OfficeExtractor`
- [ ] Crear métodos auxiliares de formateo y detección
- [ ] Actualizar configuración en `settings.py`

### Fase 2: Integración (1 hora)
- [ ] Actualizar `extract_full_content_from_file()` 
- [ ] Probar con archivos Excel de ejemplo
- [ ] Verificar límites de performance
- [ ] Ajustar logging y métricas

### Fase 3: Detección de Seguridad (1-2 horas)
- [ ] Implementar patrones de detección sensible
- [ ] Crear análisis de riesgo automático
- [ ] Agregar alertas específicas para Excel
- [ ] Documentar casos de uso de seguridad

### Fase 4: Testing y Optimización (1 hora)
- [ ] Probar con archivos XLS y XLSX reales
- [ ] Verificar performance con archivos grandes
- [ ] Optimizar consultas y memoria
- [ ] Validar límites configurados

## Dependencias Adicionales

### Librerías Requeridas
```bash
# Ya instaladas en requirements.txt
openpyxl==3.1.2  # Para archivos XLSX ✅

# Opcionales para XLS legacy
xlrd==2.0.1      # Para archivos XLS legacy (opcional)
```

### Instalación Opcional XLS
```bash
# Solo si se necesita soporte robusto para XLS muy antiguos
pip install xlrd==2.0.1
```

**Nota**: `openpyxl` puede leer algunos archivos XLS modernos, por lo que `xlrd` es opcional.

## Riesgos y Mitigaciones

### Riesgos Técnicos

#### Performance
- **Riesgo**: Archivos Excel muy grandes consumen mucha memoria
- **Mitigación**: Límites estrictos por hoja y por archivo
- **Monitoreo**: Timeout de 60 segundos por archivo

#### Compatibilidad
- **Riesgo**: Archivos XLS muy antiguos o corruptos
- **Mitigación**: Múltiples métodos de extracción (xlrd, openpyxl)
- **Fallback**: Continuar con metadatos básicos si falla contenido

#### Contenido Sensible
- **Riesgo**: Exposición accidental de información confidencial
- **Mitigación**: Marcado de contenido sensible, límites de caracteres
- **Auditoría**: Logging detallado de qué se extrae

### Riesgos de Seguridad

#### Información Personal Expuesta
- **Riesgo**: Extracción de datos personales sin consentimiento
- **Mitigación**: Solo para análisis de seguridad defensiva
- **Control**: Configuración para deshabilitar detección sensible

#### Archivos Maliciosos
- **Riesgo**: Archivos Excel con macros o contenido malicioso
- **Mitigación**: Solo lectura, sin ejecución de macros
- **Límites**: Timeout y sandbox de procesamiento

## Métricas de Éxito

### Cobertura Funcional
- **Objetivo**: >90% de archivos Excel procesados exitosamente
- **XLSX**: 95% de éxito esperado
- **XLS**: 80% de éxito esperado (formatos legacy)

### Performance
- **Tiempo promedio**: <10 segundos por archivo Excel
- **Memoria máxima**: <100MB por proceso
- **Contenido extraído**: 500-5000 caracteres promedio por archivo

### Detección de Seguridad
- **Información sensible**: >70% de patrones detectados correctamente
- **Falsos positivos**: <10% de detecciones incorrectas
- **Casos de alto riesgo**: 100% de archivos con nombres sospechosos alertados

## Documentación de Casos de Uso

### Ejemplo de Salida Esperada

#### Archivo XLSX con Datos Sensibles
```
=== HOJA: Clientes ===
Nombre | RUT | Email | Teléfono
Juan Pérez | [SENSITIVE]12.345.678-9 | [SENSITIVE]juan@empresa.cl | +56912345678
María González | [SENSITIVE]11.222.333-4 | [SENSITIVE]maria@empresa.cl | +56987654321

=== HOJA: Configuración ===
Parámetro | Valor
DB_PASSWORD | [SENSITIVE]admin123
API_KEY | [SENSITIVE]sk_live_abc123def456

=== RANGOS DEFINIDOS ===
LISTA_CLIENTES, PARAMETROS_SISTEMA
```

#### Archivo XLS Legacy
```
=== HOJA: Datos ===
Código | Descripción | Monto
001 | Factura enero | 150000.0
002 | Pago proveedores | 75000.0

(Limitado a 1000 celdas)
```

### Alertas de Seguridad Generadas
```json
{
    "file": "clientes.xlsx",
    "risk_level": "HIGH",
    "sensitive_data_count": 15,
    "alerts": [
        "rut: 2 encontrados",
        "email: 2 encontrados", 
        "Hoja de riesgo: Configuración",
        "Credenciales detectadas en contenido"
    ],
    "recommendations": [
        "Revisar archivo por información sensible",
        "Verificar si debe ser público",
        "Considerar limpieza de metadatos"
    ]
}
```

## Próximos Pasos

### Implementación Inmediata
1. **Desarrollar métodos de extracción** siguiendo la arquitectura propuesta
2. **Probar con archivos reales** del entorno de producción
3. **Ajustar límites** basado en performance observada
4. **Integrar en pipeline** de Celery existente

### Mejoras Futuras
1. **Análisis de fórmulas**: Detectar referencias sospechosas
2. **Extracción de gráficos**: Metadatos de visualizaciones
3. **Validación de datos**: Reglas de negocio embebidas
4. **Comparación de versiones**: Detectar cambios en archivos

---

*Plan de implementación - 2025-08-20*  
*Tiempo estimado de implementación: 5-7 horas*  
*Prioridad: ALTA - Información valiosa no capturada actualmente*