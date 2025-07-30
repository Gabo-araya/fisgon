# crawler/metadata_utils.py
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import re
import logging

logger = logging.getLogger('crawler')


class MetadataAnalyzer:
    """Analizador de metadatos extraídos para identificar patrones y riesgos"""
    
    def __init__(self, crawl_results):
        self.crawl_results = crawl_results
        self.analysis_results = {}
    
    def analyze_all(self) -> Dict[str, Any]:
        """Ejecuta todos los análisis disponibles"""
        self.analysis_results = {
            'authors_analysis': self.analyze_authors(),
            'software_analysis': self.analyze_software(),
            'temporal_analysis': self.analyze_temporal_patterns(),
            'location_analysis': self.analyze_location_data(),
            'risk_assessment': self.assess_security_risks(),
            'privacy_assessment': self.assess_privacy_risks(),
        }
        return self.analysis_results
    
    def analyze_authors(self) -> Dict[str, Any]:
        """Analiza patrones de autores en los documentos"""
        authors = []
        creators = []
        last_modified_by = []
        
        for result in self.crawl_results:
            metadata = result.metadata
            
            # Extraer autores de diferentes tipos de archivos
            for category in ['pdf_metadata', 'office_metadata']:
                if category in metadata:
                    cat_data = metadata[category]
                    
                    if 'author' in cat_data and cat_data['author']:
                        authors.append(self._clean_author_name(cat_data['author']))
                    
                    if 'creator' in cat_data and cat_data['creator']:
                        creators.append(self._clean_author_name(cat_data['creator']))
                    
                    if 'last_modified_by' in cat_data and cat_data['last_modified_by']:
                        last_modified_by.append(self._clean_author_name(cat_data['last_modified_by']))
        
        # Contar frecuencias
        author_counts = Counter(authors)
        creator_counts = Counter(creators)
        modifier_counts = Counter(last_modified_by)
        
        # Identificar usuarios muy activos (posible riesgo)
        high_activity_threshold = max(3, len(self.crawl_results) * 0.1)
        high_activity_authors = [
            author for author, count in author_counts.items() 
            if count >= high_activity_threshold
        ]
        
        # Detectar patrones de nombres corporativos
        corporate_patterns = self._detect_corporate_patterns(authors + creators)
        
        return {
            'total_unique_authors': len(set(authors)),
            'total_unique_creators': len(set(creators)),
            'most_frequent_authors': author_counts.most_common(10),
            'most_frequent_creators': creator_counts.most_common(10),
            'high_activity_authors': high_activity_authors,
            'corporate_patterns': corporate_patterns,
            'email_addresses_found': self._extract_email_addresses(authors + creators + last_modified_by),
        }
    
    def analyze_software(self) -> Dict[str, Any]:
        """Analiza el software utilizado para crear los documentos"""
        software_detected = []
        versions_detected = []
        
        for result in self.crawl_results:
            metadata = result.metadata
            
            # Extraer información de software
            for category in ['pdf_metadata', 'office_metadata', 'exif_metadata']:
                if category in metadata:
                    cat_data = metadata[category]
                    
                    # Software/Producer/Creator que indique herramientas
                    software_fields = ['producer', 'creator', 'software', 'encoding_software']
                    for field in software_fields:
                        if field in cat_data and cat_data[field]:
                            software_info = cat_data[field]
                            software_detected.append(software_info)
                            
                            # Extraer versión si es posible
                            version = self._extract_version(software_info)
                            if version:
                                versions_detected.append((software_info, version))
        
        software_counts = Counter(software_detected)
        
        # Detectar software desactualizado
        outdated_software = self._detect_outdated_software(versions_detected)
        
        # Categorizar por tipo de software
        software_categories = self._categorize_software(software_detected)
        
        return {
            'total_software_detected': len(set(software_detected)),
            'most_common_software': software_counts.most_common(10),
            'outdated_software': outdated_software,
            'software_categories': software_categories,
            'version_analysis': self._analyze_versions(versions_detected),
        }
    
    def analyze_temporal_patterns(self) -> Dict[str, Any]:
        """Analiza patrones temporales en las fechas de creación/modificación"""
        creation_dates = []
        modification_dates = []
        
        for result in self.crawl_results:
            metadata = result.metadata
            
            for category in ['pdf_metadata', 'office_metadata']:
                if category in metadata:
                    cat_data = metadata[category]
                    
                    # Fechas de creación
                    for date_field in ['creation_date', 'created', 'datetime_original']:
                        if date_field in cat_data and cat_data[date_field]:
                            parsed_date = self._parse_date(cat_data[date_field])
                            if parsed_date:
                                creation_dates.append(parsed_date)
                    
                    # Fechas de modificación
                    for date_field in ['modification_date', 'modified']:
                        if date_field in cat_data and cat_data[date_field]:
                            parsed_date = self._parse_date(cat_data[date_field])
                            if parsed_date:
                                modification_dates.append(parsed_date)
        
        # Análisis temporal
        date_analysis = {}
        
        if creation_dates:
            creation_dates.sort()
            date_analysis['creation_date_range'] = {
                'earliest': creation_dates[0].isoformat(),
                'latest': creation_dates[-1].isoformat(),
                'span_days': (creation_dates[-1] - creation_dates[0]).days
            }
            
            # Actividad por año/mes
            date_analysis['activity_by_year'] = self._group_dates_by_period(creation_dates, 'year')
            date_analysis['activity_by_month'] = self._group_dates_by_period(creation_dates, 'month')
            date_analysis['activity_by_weekday'] = self._group_dates_by_weekday(creation_dates)
            
            # Detectar períodos de alta actividad
            date_analysis['high_activity_periods'] = self._detect_high_activity_periods(creation_dates)
        
        return date_analysis
    
    def analyze_location_data(self) -> Dict[str, Any]:
        """Analiza datos de geolocalización en metadatos"""
        gps_coordinates = []
        location_strings = []
        
        for result in self.crawl_results:
            metadata = result.metadata
            
            # Buscar coordenadas GPS en metadatos EXIF
            if 'exif_metadata' in metadata:
                exif_data = metadata['exif_metadata']
                if 'gps_coordinates' in exif_data:
                    gps_data = exif_data['gps_coordinates']
                    if isinstance(gps_data, dict) and 'latitude' in gps_data and 'longitude' in gps_data:
                        gps_coordinates.append((gps_data['latitude'], gps_data['longitude']))
                        if 'coordinates_string' in gps_data:
                            location_strings.append(gps_data['coordinates_string'])
        
        location_analysis = {
            'total_files_with_gps': len(gps_coordinates),
            'unique_locations': len(set(gps_coordinates)),
            'coordinates_found': gps_coordinates,
        }
        
        if gps_coordinates:
            # Calcular centro geográfico
            avg_lat = sum(coord[0] for coord in gps_coordinates) / len(gps_coordinates)
            avg_lon = sum(coord[1] for coord in gps_coordinates) / len(gps_coordinates)
            location_analysis['geographic_center'] = (avg_lat, avg_lon)
            
            # Detectar clustering de ubicaciones
            location_analysis['location_clusters'] = self._detect_location_clusters(gps_coordinates)
        
        return location_analysis
    
    def assess_security_risks(self) -> Dict[str, Any]:
        """Evalúa riesgos de seguridad basados en los metadatos"""
        risks = []
        risk_score = 0
        
        # Riesgo por software desactualizado
        software_analysis = self.analysis_results.get('software_analysis', {})
        outdated_software = software_analysis.get('outdated_software', [])
        
        if outdated_software:
            risk_level = min(len(outdated_software) * 2, 10)
            risks.append({
                'type': 'outdated_software',
                'level': risk_level,
                'description': f'Se detectaron {len(outdated_software)} herramientas de software desactualizadas',
                'affected_items': len(outdated_software),
                'recommendation': 'Actualizar software para evitar vulnerabilidades conocidas'
            })
            risk_score += risk_level
        
        # Riesgo por exposición de nombres de usuario
        authors_analysis = self.analysis_results.get('authors_analysis', {})
        email_addresses = authors_analysis.get('email_addresses_found', [])
        
        if email_addresses:
            risk_level = min(len(email_addresses), 8)
            risks.append({
                'type': 'user_exposure',
                'level': risk_level,
                'description': f'Se encontraron {len(email_addresses)} direcciones de correo en metadatos',
                'affected_items': len(email_addresses),
                'recommendation': 'Configurar herramientas para no incluir información personal en metadatos'
            })
            risk_score += risk_level
        
        # Riesgo por información corporativa
        corporate_patterns = authors_analysis.get('corporate_patterns', [])
        if corporate_patterns:
            risk_level = min(len(corporate_patterns) * 1.5, 6)
            risks.append({
                'type': 'corporate_info_exposure',
                'level': risk_level,
                'description': f'Se detectaron {len(corporate_patterns)} patrones de información corporativa',
                'affected_items': len(corporate_patterns),
                'recommendation': 'Revisar configuración de plantillas corporativas'
            })
            risk_score += risk_level
        
        return {
            'overall_risk_score': min(risk_score, 10),
            'risk_level': self._calculate_risk_level(risk_score),
            'identified_risks': risks,
            'total_risk_factors': len(risks),
        }
    
    def assess_privacy_risks(self) -> Dict[str, Any]:
        """Evalúa riesgos de privacidad"""
        privacy_risks = []
        privacy_score = 0
        
        # Riesgo por coordenadas GPS
        location_analysis = self.analysis_results.get('location_analysis', {})
        files_with_gps = location_analysis.get('total_files_with_gps', 0)
        
        if files_with_gps > 0:
            risk_level = min(files_with_gps * 2, 10)
            privacy_risks.append({
                'type': 'location_exposure',
                'level': risk_level,
                'description': f'{files_with_gps} archivos contienen coordenadas GPS',
                'affected_items': files_with_gps,
                'recommendation': 'Eliminar metadatos EXIF antes de publicar imágenes'
            })
            privacy_score += risk_level
        
        # Riesgo por información personal en autores
        authors_analysis = self.analysis_results.get('authors_analysis', {})
        unique_authors = authors_analysis.get('total_unique_authors', 0)
        
        if unique_authors > 0:
            risk_level = min(unique_authors * 0.5, 5)
            privacy_risks.append({
                'type': 'personal_info_exposure',
                'level': risk_level,
                'description': f'Se identificaron {unique_authors} autores únicos en los documentos',
                'affected_items': unique_authors,
                'recommendation': 'Usar usuarios genéricos para la creación de documentos públicos'
            })
            privacy_score += risk_level
        
        return {
            'overall_privacy_score': min(privacy_score, 10),
            'privacy_level': self._calculate_risk_level(privacy_score),
            'identified_privacy_risks': privacy_risks,
            'total_privacy_factors': len(privacy_risks),
        }
    
    # Métodos auxiliares
    def _clean_author_name(self, author: str) -> str:
        """Limpia y normaliza nombres de autores"""
        if not author:
            return ""
        
        # Remover caracteres especiales y espacios extra
        cleaned = re.sub(r'[^\w\s@.-]', '', str(author)).strip()
        
        # Normalizar espacios
        cleaned = ' '.join(cleaned.split())
        
        return cleaned
    
    def _detect_corporate_patterns(self, names: List[str]) -> List[str]:
        """Detecta patrones corporativos en nombres"""
        corporate_indicators = [
            'empresa', 'company', 'corp', 'inc', 'ltd', 'sa', 'ltda',
            'administrator', 'admin', 'user', 'usuario', 'corporativo'
        ]
        
        patterns = []
        for name in names:
            name_lower = name.lower()
            for indicator in corporate_indicators:
                if indicator in name_lower:
                    patterns.append(name)
                    break
        
        return list(set(patterns))
    
    def _extract_email_addresses(self, text_list: List[str]) -> List[str]:
        """Extrae direcciones de correo electrónico"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = []
        
        for text in text_list:
            if text:
                found_emails = re.findall(email_pattern, str(text))
                emails.extend(found_emails)
        
        return list(set(emails))
    
    def _extract_version(self, software_string: str) -> str:
        """Extrae número de versión de string de software"""
        if not software_string:
            return ""
        
        # Patrones comunes de versión
        version_patterns = [
            r'(\d+\.\d+\.\d+)',  # x.y.z
            r'(\d+\.\d+)',       # x.y
            r'(\d{4})',          # año
            r'v(\d+\.\d+)',      # v x.y
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, software_string)
            if match:
                return match.group(1)
        
        return ""
    
    def _detect_outdated_software(self, versions: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """Detecta software desactualizado"""
        current_year = datetime.now().year
        outdated = []
        
        # Lista de software conocido con años de lanzamiento
        known_software = {
            'Adobe Acrobat': {'latest_major': 2023, 'support_years': 3},
            'Microsoft Office': {'latest_major': 2021, 'support_years': 5},
            'Microsoft Word': {'latest_major': 2021, 'support_years': 5},
            'LibreOffice': {'latest_major': 2023, 'support_years': 2},
        }
        
        for software, version in versions:
            # Detectar año en la versión o nombre del software
            year_match = re.search(r'(20\d{2})', software + ' ' + version)
            if year_match:
                software_year = int(year_match.group(1))
                if current_year - software_year > 5:  # Más de 5 años
                    outdated.append({
                        'software': software,
                        'version': version,
                        'year': software_year,
                        'age_years': current_year - software_year,
                        'risk_level': min((current_year - software_year) // 2, 10)
                    })
        
        return outdated
    
    def _categorize_software(self, software_list: List[str]) -> Dict[str, List[str]]:
        """Categoriza software por tipo"""
        categories = defaultdict(list)
        
        category_keywords = {
            'pdf_tools': ['acrobat', 'pdf', 'foxit'],
            'office_suite': ['microsoft', 'office', 'word', 'excel', 'powerpoint', 'libreoffice'],
            'image_editors': ['photoshop', 'gimp', 'paint', 'lightroom'],
            'other': []
        }
        
        for software in software_list:
            software_lower = software.lower()
            categorized = False
            
            for category, keywords in category_keywords.items():
                if category == 'other':
                    continue
                
                for keyword in keywords:
                    if keyword in software_lower:
                        categories[category].append(software)
                        categorized = True
                        break
                
                if categorized:
                    break
            
            if not categorized:
                categories['other'].append(software)
        
        return dict(categories)
    
    def _analyze_versions(self, versions: List[Tuple[str, str]]) -> Dict[str, Any]:
        """Analiza distribución de versiones"""
        version_counts = Counter([version for software, version in versions])
        
        return {
            'total_versions_detected': len(version_counts),
            'most_common_versions': version_counts.most_common(5),
            'version_diversity': len(set([version for software, version in versions]))
        }
    
    def _parse_date(self, date_string: str) -> datetime:
        """Parsea string de fecha a objeto datetime"""
        if not date_string:
            return None
        
        # Formatos comunes de fecha
        date_formats = [
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%Y:%m:%d %H:%M:%S',  # EXIF format
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_string[:len(fmt)], fmt)
            except ValueError:
                continue
        
        return None
    
    def _group_dates_by_period(self, dates: List[datetime], period: str) -> Dict[str, int]:
        """Agrupa fechas por período (year, month)"""
        grouped = defaultdict(int)
        
        for date in dates:
            if period == 'year':
                key = str(date.year)
            elif period == 'month':
                key = f"{date.year}-{date.month:02d}"
            else:
                key = date.strftime('%Y-%m-%d')
            
            grouped[key] += 1
        
        return dict(grouped)
    
    def _group_dates_by_weekday(self, dates: List[datetime]) -> Dict[str, int]:
        """Agrupa fechas por día de la semana"""
        weekdays = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        grouped = defaultdict(int)
        
        for date in dates:
            weekday_name = weekdays[date.weekday()]
            grouped[weekday_name] += 1
        
        return dict(grouped)
    
    def _detect_high_activity_periods(self, dates: List[datetime]) -> List[Dict[str, Any]]:
        """Detecta períodos de alta actividad"""
        if not dates:
            return []
        
        # Agrupar por semana
        week_counts = defaultdict(int)
        for date in dates:
            week_key = date.strftime('%Y-W%U')
            week_counts[week_key] += 1
        
        # Calcular promedio y detectar picos
        avg_activity = sum(week_counts.values()) / len(week_counts)
        threshold = avg_activity * 1.5
        
        high_activity = []
        for week, count in week_counts.items():
            if count > threshold:
                high_activity.append({
                    'period': week,
                    'activity_count': count,
                    'above_average_ratio': count / avg_activity
                })
        
        return high_activity
    
    def _detect_location_clusters(self, coordinates: List[Tuple[float, float]]) -> List[Dict[str, Any]]:
        """Detecta clusters de ubicaciones GPS"""
        if len(coordinates) < 2:
            return []
        
        # Algoritmo simple de clustering por proximidad
        clusters = []
        processed = set()
        
        for i, coord1 in enumerate(coordinates):
            if i in processed:
                continue
            
            cluster = [coord1]
            processed.add(i)
            
            for j, coord2 in enumerate(coordinates[i+1:], i+1):
                if j in processed:
                    continue
                
                # Calcular distancia aproximada (en grados)
                distance = ((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)**0.5
                
                if distance < 0.01:  # Aproximadamente 1km
                    cluster.append(coord2)
                    processed.add(j)
            
            if len(cluster) > 1:
                # Calcular centro del cluster
                center_lat = sum(coord[0] for coord in cluster) / len(cluster)
                center_lon = sum(coord[1] for coord in cluster) / len(cluster)
                
                clusters.append({
                    'center': (center_lat, center_lon),
                    'coordinates': cluster,
                    'size': len(cluster)
                })
        
        return clusters
    
    def _calculate_risk_level(self, score: float) -> str:
        """Convierte score numérico a nivel de riesgo"""
        if score <= 2:
            return 'Bajo'
        elif score <= 5:
            return 'Medio'
        elif score <= 8:
            return 'Alto'
        else:
            return 'Crítico'


def analyze_session_metadata(session):
    """Función de conveniencia para analizar metadatos de una sesión completa"""
    from .models import CrawlResult
    
    results = CrawlResult.objects.filter(
        session=session
    ).exclude(metadata={})
    
    if not results.exists():
        return {
            'error': 'No se encontraron resultados con metadatos para esta sesión'
        }
    
    analyzer = MetadataAnalyzer(results)
    analysis = analyzer.analyze_all()
    
    return analysis