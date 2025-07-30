# crawler/extractors.py
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import hashlib

logger = logging.getLogger('crawler')

# Librerías para extracción de metadatos
try:
    import PyPDF2
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("PyPDF2 no disponible. Instalar con: pip install PyPDF2")

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    logger.warning("Pillow no disponible. Instalar con: pip install Pillow")

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logger.warning("python-docx no disponible. Instalar con: pip install python-docx")

try:
    from openpyxl import load_workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    logger.warning("openpyxl no disponible. Instalar con: pip install openpyxl")

try:
    from mutagen import File as MutagenFile
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    logger.warning("mutagen no disponible. Instalar con: pip install mutagen")

try:
    import json
    import xml.etree.ElementTree as ET
    XML_JSON_AVAILABLE = True
except ImportError:
    XML_JSON_AVAILABLE = False


class MetadataExtractor:
    '''Clase base para extractores de metadatos'''
    
    def __init__(self, file_path: str, file_url: str = None, referrer: str = None):
        self.file_path = file_path
        self.file_url = file_url
        self.referrer = referrer
        self.metadata = {}
    
    def extract(self) -> Dict[str, Any]:
        '''Método principal que debe ser implementado por cada extractor'''
        raise NotImplementedError
    
    def get_common_metadata(self) -> Dict[str, Any]:
        '''Obtiene metadatos comunes a todos los archivos'''
        try:
            stat_info = os.stat(self.file_path)
            file_hash = self._calculate_file_hash()
            
            return {
                'file_path': self.file_path,
                'file_url': self.file_url,
                'referrer': self.referrer,
                'file_size': stat_info.st_size,
                'file_hash_sha256': file_hash,
                'created_at': datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                'extracted_at': datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error obteniendo metadatos comunes: {str(e)}")
            return {}
    
    def _calculate_file_hash(self) -> str:
        '''Calcula el hash SHA-256 del archivo'''
        try:
            with open(self.file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""


class PDFExtractor(MetadataExtractor):
    '''Extractor especializado para archivos PDF'''
    
    def extract(self) -> Dict[str, Any]:
        metadata = self.get_common_metadata()
        
        if not PDF_AVAILABLE:
            logger.warning("PyPDF2 no disponible, extracción limitada")
            return metadata
        
        try:
            with open(self.file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                
                # Metadatos del documento
                if pdf_reader.metadata:
                    pdf_metadata = {
                        'author': self._clean_text(pdf_reader.metadata.get('/Author', '')),
                        'creator': self._clean_text(pdf_reader.metadata.get('/Creator', '')),
                        'producer': self._clean_text(pdf_reader.metadata.get('/Producer', '')),
                        'title': self._clean_text(pdf_reader.metadata.get('/Title', '')),
                        'subject': self._clean_text(pdf_reader.metadata.get('/Subject', '')),
                        'keywords': self._clean_text(pdf_reader.metadata.get('/Keywords', '')),
                        'creation_date': self._parse_pdf_date(pdf_reader.metadata.get('/CreationDate')),
                        'modification_date': self._parse_pdf_date(pdf_reader.metadata.get('/ModDate')),
                    }
                    
                    # Filtrar valores vacíos
                    pdf_metadata = {k: v for k, v in pdf_metadata.items() if v}
                    metadata['pdf_metadata'] = pdf_metadata
                
                # Información del PDF
                metadata['pdf_info'] = {
                    'num_pages': len(pdf_reader.pages),
                    'encrypted': pdf_reader.is_encrypted,
                    'pdf_version': getattr(pdf_reader, 'pdf_header', '').replace('%PDF-', '') if hasattr(pdf_reader, 'pdf_header') else '',
                }
                
                # Extraer texto de la primera página para análisis
                if len(pdf_reader.pages) > 0:
                    first_page_text = pdf_reader.pages[0].extract_text()[:500]
                    metadata['first_page_preview'] = first_page_text
                
        except Exception as e:
            logger.error(f"Error extrayendo metadatos de PDF {self.file_path}: {str(e)}")
            metadata['extraction_error'] = str(e)
        
        return metadata
    
    def _clean_text(self, text: str) -> str:
        '''Limpia texto de caracteres especiales de PDF'''
        if not text:
            return ""
        return text.strip().replace('\x00', '').replace('\r', '').replace('\n', ' ')
    
    def _parse_pdf_date(self, date_str: str) -> str:
        '''Parsea fechas en formato PDF a ISO'''
        if not date_str:
            return ""
        
        try:
            # Formato típico: D:20230515143022+05'00'
            if date_str.startswith('D:'):
                date_part = date_str[2:16]  # YYYYMMDDHHMMSS
                if len(date_part) >= 8:
                    year = date_part[:4]
                    month = date_part[4:6]
                    day = date_part[6:8]
                    hour = date_part[8:10] if len(date_part) >= 10 else "00"
                    minute = date_part[10:12] if len(date_part) >= 12 else "00"
                    second = date_part[12:14] if len(date_part) >= 14 else "00"
                    
                    return f"{year}-{month}-{day}T{hour}:{minute}:{second}"
        except Exception:
            pass
        
        return str(date_str)


class ImageExtractor(MetadataExtractor):
    '''Extractor especializado para imágenes (JPEG, PNG, TIFF, etc.)'''
    
    def extract(self) -> Dict[str, Any]:
        metadata = self.get_common_metadata()
        
        if not PILLOW_AVAILABLE:
            logger.warning("Pillow no disponible, extracción limitada")
            return metadata
        
        try:
            with Image.open(self.file_path) as image:
                # Información básica de la imagen
                metadata['image_info'] = {
                    'format': image.format,
                    'mode': image.mode,
                    'size': image.size,
                    'width': image.width,
                    'height': image.height,
                }
                
                # Extraer EXIF si está disponible
                if hasattr(image, '_getexif') and image._getexif():
                    exif_data = image._getexif()
                    if exif_data:
                        exif_metadata = {}
                        
                        for tag_id, value in exif_data.items():
                            tag = TAGS.get(tag_id, tag_id)
                            
                            # Procesar tags importantes
                            if tag == 'DateTime':
                                exif_metadata['datetime_original'] = str(value)
                            elif tag == 'DateTimeOriginal':
                                exif_metadata['datetime_original'] = str(value)
                            elif tag == 'Make':
                                exif_metadata['camera_make'] = str(value)
                            elif tag == 'Model':
                                exif_metadata['camera_model'] = str(value)
                            elif tag == 'Software':
                                exif_metadata['software'] = str(value)
                            elif tag == 'Artist':
                                exif_metadata['artist'] = str(value)
                            elif tag == 'Copyright':
                                exif_metadata['copyright'] = str(value)
                            elif tag == 'GPSInfo':
                                gps_data = self._extract_gps_data(value)
                                if gps_data:
                                    exif_metadata['gps_coordinates'] = gps_data
                        
                        if exif_metadata:
                            metadata['exif_metadata'] = exif_metadata
                
        except Exception as e:
            logger.error(f"Error extrayendo metadatos de imagen {self.file_path}: {str(e)}")
            metadata['extraction_error'] = str(e)
        
        return metadata
    
    def _extract_gps_data(self, gps_info: dict) -> Optional[Dict[str, Any]]:
        '''Extrae y convierte coordenadas GPS'''
        try:
            gps_data = {}
            
            for tag_id, value in gps_info.items():
                tag = GPSTAGS.get(tag_id, tag_id)
                gps_data[tag] = value
            
            # Convertir coordenadas a decimal
            if 'GPSLatitude' in gps_data and 'GPSLongitude' in gps_data:
                lat = self._convert_to_degrees(gps_data['GPSLatitude'])
                lon = self._convert_to_degrees(gps_data['GPSLongitude'])
                
                # Aplicar signos según hemisferio
                if gps_data.get('GPSLatitudeRef') == 'S':
                    lat = -lat
                if gps_data.get('GPSLongitudeRef') == 'W':
                    lon = -lon
                
                return {
                    'latitude': lat,
                    'longitude': lon,
                    'coordinates_string': f"({lat:.6f}, {lon:.6f})"
                }
        
        except Exception as e:
            logger.error(f"Error procesando GPS: {str(e)}")
        
        return None
    
    def _convert_to_degrees(self, value):
        '''Convierte coordenadas GPS de grados/minutos/segundos a decimal'''
        d, m, s = value
        return float(d) + float(m)/60.0 + float(s)/3600.0


class OfficeExtractor(MetadataExtractor):
    '''Extractor para documentos de Microsoft Office (Word, Excel, PowerPoint)'''
    
    def extract(self) -> Dict[str, Any]:
        metadata = self.get_common_metadata()
        
        file_extension = os.path.splitext(self.file_path)[1].lower()
        
        if file_extension in ['.docx']:
            return self._extract_docx_metadata(metadata)
        elif file_extension in ['.xlsx']:
            return self._extract_xlsx_metadata(metadata)
        else:
            # Para otros formatos de Office (.doc, .xls, .ppt)
            metadata['office_format'] = file_extension
            metadata['extraction_note'] = 'Formato de Office legacy, extracción limitada'
        
        return metadata
    
    def _extract_docx_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        '''Extrae metadatos de documentos Word (.docx)'''
        if not DOCX_AVAILABLE:
            metadata['extraction_error'] = 'python-docx no disponible'
            return metadata
        
        try:
            doc = Document(self.file_path)
            core_props = doc.core_properties
            
            office_metadata = {}
            
            # Propiedades principales
            if core_props.author:
                office_metadata['author'] = core_props.author
            if core_props.last_modified_by:
                office_metadata['last_modified_by'] = core_props.last_modified_by
            if core_props.created:
                office_metadata['created'] = core_props.created.isoformat()
            if core_props.modified:
                office_metadata['modified'] = core_props.modified.isoformat()
            if core_props.title:
                office_metadata['title'] = core_props.title
            if core_props.subject:
                office_metadata['subject'] = core_props.subject
            if core_props.keywords:
                office_metadata['keywords'] = core_props.keywords
            if core_props.comments:
                office_metadata['comments'] = core_props.comments
            if core_props.category:
                office_metadata['category'] = core_props.category
            if core_props.revision:
                office_metadata['revision'] = core_props.revision
            
            metadata['office_metadata'] = office_metadata
            
            # Información del documento
            metadata['document_info'] = {
                'paragraphs_count': len(doc.paragraphs),
                'document_type': 'Word Document (.docx)'
            }
            
            # Extraer texto inicial para análisis
            first_paragraphs = []
            for para in doc.paragraphs[:3]:
                if para.text.strip():
                    first_paragraphs.append(para.text.strip())
            
            if first_paragraphs:
                metadata['content_preview'] = ' '.join(first_paragraphs)[:500]
            
        except Exception as e:
            logger.error(f"Error extrayendo metadatos de DOCX {self.file_path}: {str(e)}")
            metadata['extraction_error'] = str(e)
        
        return metadata
    
    def _extract_xlsx_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        '''Extrae metadatos de hojas de cálculo Excel (.xlsx)'''
        if not OPENPYXL_AVAILABLE:
            metadata['extraction_error'] = 'openpyxl no disponible'
            return metadata
        
        try:
            workbook = load_workbook(self.file_path, data_only=True)
            
            office_metadata = {}
            
            # Propiedades del workbook
            props = workbook.properties
            if props.creator:
                office_metadata['creator'] = props.creator
            if props.lastModifiedBy:
                office_metadata['last_modified_by'] = props.lastModifiedBy
            if props.created:
                office_metadata['created'] = props.created.isoformat()
            if props.modified:
                office_metadata['modified'] = props.modified.isoformat()
            if props.title:
                office_metadata['title'] = props.title
            if props.subject:
                office_metadata['subject'] = props.subject
            if props.keywords:
                office_metadata['keywords'] = props.keywords
            if props.description:
                office_metadata['description'] = props.description
            if props.category:
                office_metadata['category'] = props.category
            if props.company:
                office_metadata['company'] = props.company
            
            metadata['office_metadata'] = office_metadata
            
            # Información de las hojas
            sheets_info = []
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                sheets_info.append({
                    'name': sheet_name,
                    'max_row': sheet.max_row,
                    'max_column': sheet.max_column
                })
            
            metadata['sheets_info'] = sheets_info
            metadata['document_info'] = {
                'sheets_count': len(workbook.sheetnames),
                'document_type': 'Excel Workbook (.xlsx)'
            }
            
        except Exception as e:
            logger.error(f"Error extrayendo metadatos de XLSX {self.file_path}: {str(e)}")
            metadata['extraction_error'] = str(e)
        
        return metadata


class MultimediaExtractor(MetadataExtractor):
    '''Extractor para archivos multimedia (MP3, MP4, etc.)'''
    
    def extract(self) -> Dict[str, Any]:
        metadata = self.get_common_metadata()
        
        if not MUTAGEN_AVAILABLE:
            metadata['extraction_error'] = 'mutagen no disponible'
            return metadata
        
        try:
            audio_file = MutagenFile(self.file_path)
            
            if audio_file is None:
                metadata['extraction_error'] = 'Formato multimedia no soportado'
                return metadata
            
            multimedia_metadata = {}
            
            # Metadatos comunes de audio
            if hasattr(audio_file, 'tags') and audio_file.tags:
                tags = audio_file.tags
                
                # MP3 tags
                if isinstance(audio_file, MP3):
                    multimedia_metadata.update(self._extract_mp3_tags(tags))
                # MP4 tags
                elif isinstance(audio_file, MP4):
                    multimedia_metadata.update(self._extract_mp4_tags(tags))
                else:
                    # Tags genéricos
                    for key, value in tags.items():
                        multimedia_metadata[str(key)] = str(value[0]) if isinstance(value, list) else str(value)
            
            # Información del archivo multimedia
            if hasattr(audio_file, 'info'):
                info = audio_file.info
                multimedia_metadata['duration_seconds'] = getattr(info, 'length', 0)
                multimedia_metadata['bitrate'] = getattr(info, 'bitrate', 0)
                multimedia_metadata['sample_rate'] = getattr(info, 'sample_rate', 0)
                multimedia_metadata['channels'] = getattr(info, 'channels', 0)
            
            metadata['multimedia_metadata'] = multimedia_metadata
            
        except Exception as e:
            logger.error(f"Error extrayendo metadatos multimedia {self.file_path}: {str(e)}")
            metadata['extraction_error'] = str(e)
        
        return metadata
    
    def _extract_mp3_tags(self, tags) -> Dict[str, Any]:
        '''Extrae tags específicos de MP3'''
        mp3_metadata = {}
        
        # Mapeo de tags ID3
        tag_mapping = {
            'TIT2': 'title',
            'TPE1': 'artist',
            'TALB': 'album',
            'TDRC': 'year',
            'TCON': 'genre',
            'TRCK': 'track_number',
            'TPE2': 'album_artist',
            'TPOS': 'disc_number',
            'TCOP': 'copyright',
            'TENC': 'encoded_by',
            'TSSE': 'encoding_software',
        }
        
        for tag_id, tag_name in tag_mapping.items():
            if tag_id in tags:
                mp3_metadata[tag_name] = str(tags[tag_id][0])
        
        return mp3_metadata
    
    def _extract_mp4_tags(self, tags) -> Dict[str, Any]:
        '''Extrae tags específicos de MP4'''
        mp4_metadata = {}
        
        # Mapeo de tags MP4
        tag_mapping = {
            '\xa9nam': 'title',
            '\xa9ART': 'artist',
            '\xa9alb': 'album',
            '\xa9day': 'year',
            '\xa9gen': 'genre',
            'trkn': 'track_number',
            '\xa9cpy': 'copyright',
            '\xa9too': 'encoding_software',
        }
        
        for tag_id, tag_name in tag_mapping.items():
            if tag_id in tags:
                value = tags[tag_id][0]
                mp4_metadata[tag_name] = str(value)
        
        return mp4_metadata


class HTMLExtractor(MetadataExtractor):
    '''Extractor para páginas HTML'''
    
    def extract(self) -> Dict[str, Any]:
        metadata = self.get_common_metadata()
        
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            html_metadata = {}
            
            # Meta tags
            meta_tags = soup.find_all('meta')
            for meta in meta_tags:
                if meta.get('name'):
                    html_metadata[f"meta_{meta.get('name')}"] = meta.get('content', '')
                elif meta.get('property'):
                    html_metadata[f"property_{meta.get('property')}"] = meta.get('content', '')
            
            # Título
            title_tag = soup.find('title')
            if title_tag:
                html_metadata['title'] = title_tag.get_text().strip()
            
            # Enlaces
            links = soup.find_all('a', href=True)
            html_metadata['links_count'] = len(links)
            
            # Imágenes
            images = soup.find_all('img', src=True)
            html_metadata['images_count'] = len(images)
            
            metadata['html_metadata'] = html_metadata
            
        except Exception as e:
            logger.error(f"Error extrayendo metadatos HTML {self.file_path}: {str(e)}")
            metadata['extraction_error'] = str(e)
        
        return metadata


# Factory function para obtener el extractor apropiado
def get_metadata_extractor(file_path: str, file_url: str = None, referrer: str = None) -> MetadataExtractor:
    '''
    Factory function que retorna el extractor apropiado según el tipo de archivo
    '''
    file_extension = os.path.splitext(file_path)[1].lower()
    
    # Mapeo de extensiones a extractores
    if file_extension == '.pdf':
        return PDFExtractor(file_path, file_url, referrer)
    elif file_extension in ['.jpg', '.jpeg', '.png', '.tiff', '.gif']:
        return ImageExtractor(file_path, file_url, referrer)
    elif file_extension in ['.docx', '.xlsx', '.pptx']:
        return OfficeExtractor(file_path, file_url, referrer)
    elif file_extension in ['.mp3', '.mp4']:
        return MultimediaExtractor(file_path, file_url, referrer)
    elif file_extension in ['.html', '.htm']:
        return HTMLExtractor(file_path, file_url, referrer)
    else:
        # Extractor genérico para otros tipos
        return MetadataExtractor(file_path, file_url, referrer)


def extract_metadata_from_file(file_path: str, file_url: str = None, referrer: str = None) -> Dict[str, Any]:
    '''
    Función principal para extraer metadatos de cualquier archivo
    '''
    try:
        extractor = get_metadata_extractor(file_path, file_url, referrer)
        return extractor.extract()
    except Exception as e:
        logger.error(f"Error en extracción de metadatos para {file_path}: {str(e)}")
        return {
            'file_path': file_path,
            'file_url': file_url,
            'referrer': referrer,
            'extraction_error': str(e),
            'extracted_at': datetime.now().isoformat(),
        }