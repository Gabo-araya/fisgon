#!/usr/bin/env python3
"""
Test script para verificar extracción de contenido completo de archivos Excel
"""

import sys
import os

# Agregar el directorio del proyecto al path
sys.path.append('/home/gabo/proy/django_proy/fisgon')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from crawler.extractors import extract_full_content_from_file

def test_excel_extraction():
    """Probar extracción de contenido de archivos Excel"""
    
    # Archivos de prueba
    files = [
        'test_files/test_excel.xlsx',
        'test_files/test_excel.xls'
    ]

    for file_path in files:
        print(f'\n=== PROBANDO: {file_path} ===')
        
        # Verificar que el archivo existe
        if not os.path.exists(file_path):
            print(f'❌ Archivo no encontrado: {file_path}')
            continue
            
        try:
            # Extraer contenido completo
            content = extract_full_content_from_file(file_path)
            
            # Simular el procesamiento que haría Celery
            if content and content.strip():
                # Aplicar límite de 1M caracteres (como en la task de Celery)
                limited_content = content[:1000000]
                content_length = len(content)
                
                print(f'✅ Contenido extraído: {content_length} caracteres')
                print(f'✅ Contenido limitado: {len(limited_content)} caracteres')
                print(f'✅ Detecta información sensible: {"[SENSITIVE]" in content}')
                
                # Contar patrones sensibles
                sensitive_count = content.count('[SENSITIVE]')
                print(f'✅ Patrones sensibles detectados: {sensitive_count}')
                
                # Mostrar primeras líneas como preview
                lines = content.split('\n')[:10]  # Primeras 10 líneas
                print('📄 Preview del contenido:')
                for line in lines:
                    print(f'   {line}')
                
                if len(lines) >= 10:
                    print('   ...')
                    
            else:
                print('❌ No se extrajo contenido')
                
        except Exception as e:
            print(f'❌ Error procesando {file_path}: {str(e)}')
            import traceback
            traceback.print_exc()

def test_sensitive_detection():
    """Probar específicamente la detección de datos sensibles"""
    print('\n=== PRUEBA DE DETECCIÓN SENSIBLE ===')
    
    # Importar función de detección
    from crawler.extractors import OfficeExtractor
    
    extractor = OfficeExtractor("dummy_path")
    
    # Casos de prueba
    test_cases = [
        ("12.345.678-9", True, "RUT chileno"),
        ("juan@empresa.cl", True, "Email"),
        ("+56912345678", True, "Teléfono chileno"), 
        ("password123", True, "Palabra clave sensible"),
        ("4532-1234-5678-9012", True, "Número de tarjeta"),
        ("Texto normal", False, "Texto normal"),
        ("123456", False, "Número simple"),
        ("", False, "Texto vacío")
    ]
    
    for text, expected, description in test_cases:
        result = extractor._contains_sensitive_pattern(text)
        status = "✅" if result == expected else "❌"
        print(f'{status} {description}: "{text}" -> {result} (esperado: {expected})')

if __name__ == "__main__":
    print("🔍 INICIANDO PRUEBAS DE EXTRACCIÓN EXCEL")
    print("=" * 60)
    
    # Probar extracción de archivos
    test_excel_extraction()
    
    # Probar detección de patrones sensibles
    test_sensitive_detection()
    
    print("\n" + "=" * 60)
    print("✅ PRUEBAS COMPLETADAS")