import geopandas as gpd
import os
import zipfile
import tempfile
import shutil
from shapely.geometry import shape
from lxml import etree
from pyproj import Transformer


# Carpetas que se buscan dentro del KMZ (acepta variantes de mayúsculas/tildes)
FOLDERS_IMPACTO = ['Proyecto', 'proyecto', 'PROYECTO', 'Impacto', 'impacto']
SUBFOLDERS_IMPACTO = ['Minigranja', 'minigranja', 'MINIGRANJA', 'Solar', 'solar']
FOLDERS_COBERTURAS = [
    'Coberturas vegetales', 'coberturas vegetales',
    'COBERTURAS VEGETALES', 'Coberturas Vegetales',
    'Coberturas', 'coberturas', 'COBERTURAS'
]
FOLDERS_IGNORAR = ['Árboles', 'arboles', 'ARBOLES', 'Arboles', 'Árbol', 'Trees', 'trees']


def cargar_poligono_impacto(file_obj, filename):
    """
    Carga polígonos desde KMZ, KML o SHP (zip).
    Retorna un GeoDataFrame en WGS84.
    
    Si es un KMZ con folders ('Proyecto', 'Coberturas vegetales', etc.),
    extrae únicamente el polígono de impacto (Minigranja del folder Proyecto).
    Si no encuentra ese folder, asume que todos los polígonos son el impacto.
    """
    tmp_dir = tempfile.mkdtemp()
    filepath = os.path.join(tmp_dir, filename)

    with open(filepath, "wb") as f:
        f.write(file_obj.getbuffer())

    try:
        if filename.endswith('.kmz'):
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                zip_ref.extractall(tmp_dir)
            kml_files = [f for f in os.listdir(tmp_dir) if f.endswith('.kml')]
            if not kml_files:
                raise ValueError("No se encontró un archivo KML dentro del KMZ")
            kml_path = os.path.join(tmp_dir, kml_files[0])

            # Intentar extracción inteligente del polígono de impacto
            gdf_impacto = _extraer_impacto_de_kml(kml_path)
            if gdf_impacto is not None and not gdf_impacto.empty:
                return gdf_impacto

            # Fallback: leer todo el KML
            gdf = gpd.read_file(kml_path, driver='KML')

        elif filename.endswith('.kml'):
            gdf = _extraer_impacto_de_kml(filepath)
            if gdf is None or gdf.empty:
                gdf = gpd.read_file(filepath, driver='KML')

        elif filename.endswith('.zip'):
            gdf = gpd.read_file(f"zip://{filepath}")

        else:
            raise ValueError("Formato no soportado. Use KMZ, KML o ZIP (SHP)")

        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)
        else:
            gdf = gdf.to_crs("EPSG:4326")

        return gdf

    finally:
        shutil.rmtree(tmp_dir)


def _extraer_impacto_de_kml(kml_path):
    """
    Lee el KML y extrae solo el polígono de impacto.
    Busca en este orden:
      1. Folder 'Proyecto' > Placemark 'Minigranja'
      2. Folder 'Proyecto' > primer Placemark con polígono
      3. Si no hay folder, primer polígono del KML
    Retorna GeoDataFrame o None si falla.
    """
    try:
        tree = etree.parse(kml_path)
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}

        # Buscar folder de impacto
        folder_impacto = None
        for folder in tree.getroot().iter('{http://www.opengis.net/kml/2.2}Folder'):
            name_elem = folder.find('kml:name', ns)
            if name_elem is None or not name_elem.text:
                continue
            if name_elem.text.strip() in FOLDERS_IMPACTO:
                folder_impacto = folder
                break

        if folder_impacto is None:
            return None

        # Dentro del folder, buscar el Placemark "Minigranja"
        placemark_target = None
        for pm in folder_impacto.findall('kml:Placemark', ns):
            pm_name = pm.find('kml:name', ns)
            pm_name_text = pm_name.text.strip() if pm_name is not None and pm_name.text else ""
            if pm_name_text in SUBFOLDERS_IMPACTO:
                placemark_target = pm
                break

        # Si no encontró 'Minigranja', usar el primer polígono del folder
        if placemark_target is None:
            for pm in folder_impacto.findall('kml:Placemark', ns):
                if pm.find('.//kml:Polygon', ns) is not None:
                    placemark_target = pm
                    break

        if placemark_target is None:
            return None

        # Extraer coordenadas
        coords_elem = placemark_target.find(
            './/kml:Polygon//kml:outerBoundaryIs//kml:LinearRing//kml:coordinates', ns
        )
        if coords_elem is None or not coords_elem.text:
            return None

        from shapely.geometry import Polygon
        coords = []
        for c in coords_elem.text.strip().split():
            partes = c.split(',')
            if len(partes) >= 2:
                coords.append((float(partes[0]), float(partes[1])))
        if len(coords) < 3:
            return None

        poly = Polygon(coords)
        gdf = gpd.GeoDataFrame(
            {'name': ['Impacto']},
            geometry=[poly],
            crs="EPSG:4326"
        )
        return gdf

    except Exception:
        return None


def extraer_coberturas_de_kmz(file_obj, filename):
    """
    Lee el KMZ y extrae los polígonos de la carpeta 'Coberturas vegetales'.
    Calcula el área en hectáreas de cada polígono.

    Retorna: dict {nombre_cobertura: area_ha}
       Ej: {'Pastos limpios': 4.5011, 'Mosaico de pastos con espacios naturales': 0.1301}
       
    Si no encuentra el folder de coberturas, retorna {}.
    """
    tmp_dir = tempfile.mkdtemp()
    filepath = os.path.join(tmp_dir, filename)

    with open(filepath, "wb") as f:
        f.write(file_obj.getbuffer())

    coberturas = {}
    try:
        if filename.endswith('.kmz'):
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                zip_ref.extractall(tmp_dir)
            kml_files = [f for f in os.listdir(tmp_dir) if f.endswith('.kml')]
            if not kml_files:
                return {}
            kml_path = os.path.join(tmp_dir, kml_files[0])
        elif filename.endswith('.kml'):
            kml_path = filepath
        else:
            return {}

        tree = etree.parse(kml_path)
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}

        # Buscar folder de coberturas
        folder_coberturas = None
        for folder in tree.getroot().iter('{http://www.opengis.net/kml/2.2}Folder'):
            name_elem = folder.find('kml:name', ns)
            if name_elem is None or not name_elem.text:
                continue
            if name_elem.text.strip() in FOLDERS_COBERTURAS:
                folder_coberturas = folder
                break

        if folder_coberturas is None:
            return {}

        # Para cada Placemark, extraer nombre y calcular área
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

        for pm in folder_coberturas.findall('kml:Placemark', ns):
            pm_name = pm.find('kml:name', ns)
            if pm_name is None or not pm_name.text:
                continue
            nombre_raw = pm_name.text.strip()

            # Limpiar nombre: quitar código CLC inicial
            # "2.3.1. Pastos limpios" -> "Pastos limpios"
            # "2.4.4. Mosaico de pastos..." -> "Mosaico de pastos..."
            nombre_limpio = _limpiar_nombre_cobertura(nombre_raw)

            coords_elem = pm.find(
                './/kml:Polygon//kml:outerBoundaryIs//kml:LinearRing//kml:coordinates', ns
            )
            if coords_elem is None or not coords_elem.text:
                continue

            # Calcular área proyectando a Web Mercator (suficiente para áreas pequeñas)
            coords = []
            for c in coords_elem.text.strip().split():
                partes = c.split(',')
                if len(partes) >= 2:
                    lon, lat = float(partes[0]), float(partes[1])
                    x, y = transformer.transform(lon, lat)
                    coords.append((x, y))
            if len(coords) < 3:
                continue

            # Fórmula de Shoelace
            n = len(coords)
            area_m2 = 0.0
            for i in range(n):
                j = (i + 1) % n
                area_m2 += coords[i][0] * coords[j][1]
                area_m2 -= coords[j][0] * coords[i][1]
            area_ha = abs(area_m2) / 2.0 / 10000

            # Acumular si la cobertura ya existe (puede haber varios polígonos)
            if nombre_limpio in coberturas:
                coberturas[nombre_limpio] += area_ha
            else:
                coberturas[nombre_limpio] = area_ha

        return coberturas

    finally:
        shutil.rmtree(tmp_dir)


def _limpiar_nombre_cobertura(nombre_raw):
    """
    Limpia el nombre de una cobertura quitando el código CLC inicial.
    Ejemplos:
      "2.3.1. Pastos limpios" -> "Pastos limpios"
      "2.4.4. Mosaico de pastos..." -> "Mosaico de pastos..."
      "Pastos limpios" -> "Pastos limpios" (sin cambio)
    """
    import re
    # Patrón: dígitos y puntos al inicio, seguido de punto y espacio
    pattern = r'^[\d\.]+\s*[.\-]?\s*'
    return re.sub(pattern, '', nombre_raw).strip()


def validar_geometria(gdf):
    """Valida que el polígono sea válido y esté en Colombia (aprox)"""
    if gdf.empty:
        return False, "El archivo está vacío"

    geom = gdf.unary_union
    if not geom.is_valid:
        return False, "La geometría del polígono no es válida"

    bounds = geom.bounds  # (minx, miny, maxx, maxy)
    if bounds[0] < -85 or bounds[2] > -66 or bounds[1] < -5 or bounds[3] > 15:
        return False, "El polígono parece estar fuera de Colombia"

    return True, "Geometría válida"
