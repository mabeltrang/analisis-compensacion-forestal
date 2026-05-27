import geopandas as gpd
import os
import zipfile
import tempfile
import shutil
import re
from shapely.geometry import shape, Polygon

# Import lxml: si falla, lanzamos error claro en vez de fallback silencioso
try:
    from lxml import etree
    LXML_OK = True
except ImportError:
    LXML_OK = False

# Import pyproj
try:
    from pyproj import Transformer
    PYPROJ_OK = True
except ImportError:
    PYPROJ_OK = False


FOLDERS_IMPACTO = ['Proyecto', 'proyecto', 'PROYECTO', 'Impacto', 'impacto']
SUBFOLDERS_IMPACTO = ['Minigranja', 'minigranja', 'MINIGRANJA', 'Solar', 'solar']
FOLDERS_COBERTURAS = [
    'Coberturas vegetales', 'coberturas vegetales',
    'COBERTURAS VEGETALES', 'Coberturas Vegetales',
    'Coberturas', 'coberturas', 'COBERTURAS'
]
FOLDERS_IGNORAR = ['Árboles', 'arboles', 'ARBOLES', 'Arboles', 'Árbol', 'Trees', 'trees']
KML_NS = 'http://www.opengis.net/kml/2.2'


def cargar_poligono_impacto(file_obj, filename):
    tmp_dir = tempfile.mkdtemp()
    filepath = os.path.join(tmp_dir, filename)
    with open(filepath, "wb") as f:
        f.write(file_obj.getbuffer())
    try:
        if filename.lower().endswith('.kmz'):
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                zip_ref.extractall(tmp_dir)
            kml_files = [f for f in os.listdir(tmp_dir) if f.endswith('.kml')]
            if not kml_files:
                raise ValueError("No se encontró un archivo KML dentro del KMZ")
            kml_path = os.path.join(tmp_dir, kml_files[0])
            gdf_impacto = _extraer_impacto_de_kml(kml_path)
            if gdf_impacto is not None and not gdf_impacto.empty:
                return gdf_impacto
            gdf = gpd.read_file(kml_path, driver='KML')
        elif filename.lower().endswith('.kml'):
            gdf_impacto = _extraer_impacto_de_kml(filepath)
            if gdf_impacto is not None and not gdf_impacto.empty:
                return gdf_impacto
            gdf = gpd.read_file(filepath, driver='KML')
        elif filename.lower().endswith('.zip'):
            gdf = gpd.read_file(f"zip://{filepath}")
        else:
            raise ValueError("Formato no soportado")
        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)
        else:
            gdf = gdf.to_crs("EPSG:4326")
        return gdf
    finally:
        shutil.rmtree(tmp_dir)


def _extraer_impacto_de_kml(kml_path):
    if not LXML_OK:
        return None
    try:
        tree = etree.parse(kml_path)
        ns = {'kml': KML_NS}
        folder_impacto = None
        for folder in tree.getroot().iter(f'{{{KML_NS}}}Folder'):
            name_elem = folder.find('kml:name', ns)
            if name_elem is None or not name_elem.text:
                continue
            if name_elem.text.strip() in FOLDERS_IMPACTO:
                folder_impacto = folder
                break
        if folder_impacto is None:
            return None
        placemark_target = None
        for pm in folder_impacto.findall('kml:Placemark', ns):
            pm_name = pm.find('kml:name', ns)
            pm_name_text = pm_name.text.strip() if pm_name is not None and pm_name.text else ""
            if pm_name_text in SUBFOLDERS_IMPACTO:
                placemark_target = pm
                break
        if placemark_target is None:
            for pm in folder_impacto.findall('kml:Placemark', ns):
                if pm.find('.//kml:Polygon', ns) is not None:
                    placemark_target = pm
                    break
        if placemark_target is None:
            return None
        coords_elem = placemark_target.find(
            './/kml:Polygon//kml:outerBoundaryIs//kml:LinearRing//kml:coordinates', ns
        )
        if coords_elem is None or not coords_elem.text:
            return None
        coords = []
        for c in coords_elem.text.strip().split():
            partes = c.split(',')
            if len(partes) >= 2:
                coords.append((float(partes[0]), float(partes[1])))
        if len(coords) < 3:
            return None
        poly = Polygon(coords)
        return gpd.GeoDataFrame({'name': ['Impacto']}, geometry=[poly], crs="EPSG:4326")
    except Exception:
        return None


def extraer_coberturas_de_kmz(file_obj, filename):
    if not LXML_OK or not PYPROJ_OK:
        return {}
    tmp_dir = tempfile.mkdtemp()
    filepath = os.path.join(tmp_dir, filename)
    with open(filepath, "wb") as f:
        f.write(file_obj.getbuffer())
    coberturas = {}
    try:
        if filename.lower().endswith('.kmz'):
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                zip_ref.extractall(tmp_dir)
            kml_files = [f for f in os.listdir(tmp_dir) if f.endswith('.kml')]
            if not kml_files:
                return {}
            kml_path = os.path.join(tmp_dir, kml_files[0])
        elif filename.lower().endswith('.kml'):
            kml_path = filepath
        else:
            return {}
        tree = etree.parse(kml_path)
        ns = {'kml': KML_NS}
        folder_coberturas = None
        for folder in tree.getroot().iter(f'{{{KML_NS}}}Folder'):
            name_elem = folder.find('kml:name', ns)
            if name_elem is None or not name_elem.text:
                continue
            if name_elem.text.strip() in FOLDERS_COBERTURAS:
                folder_coberturas = folder
                break
        if folder_coberturas is None:
            return {}
        # FIX: usar EPSG:3116 (MAGNA-SIRGAS) en lugar de 3857 (Mercator)
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:3116", always_xy=True)
        for pm in folder_coberturas.findall('kml:Placemark', ns):
            pm_name = pm.find('kml:name', ns)
            if pm_name is None or not pm_name.text:
                continue
            nombre_raw = pm_name.text.strip()
            nombre_limpio = _limpiar_nombre_cobertura(nombre_raw)
            coords_elem = pm.find(
                './/kml:Polygon//kml:outerBoundaryIs//kml:LinearRing//kml:coordinates', ns
            )
            if coords_elem is None or not coords_elem.text:
                continue
            coords = []
            for c in coords_elem.text.strip().split():
                partes = c.split(',')
                if len(partes) >= 2:
                    lon, lat = float(partes[0]), float(partes[1])
                    x, y = transformer.transform(lon, lat)
                    coords.append((x, y))
            if len(coords) < 3:
                continue
            n = len(coords)
            area_m2 = 0.0
            for i in range(n):
                j = (i + 1) % n
                area_m2 += coords[i][0] * coords[j][1]
                area_m2 -= coords[j][0] * coords[i][1]
            area_ha = abs(area_m2) / 2.0 / 10000
            if nombre_limpio in coberturas:
                coberturas[nombre_limpio] += area_ha
            else:
                coberturas[nombre_limpio] = area_ha
        return coberturas
    finally:
        shutil.rmtree(tmp_dir)


def _limpiar_nombre_cobertura(nombre_raw):
    pattern = r'^[\d\.]+\s*[.\-]?\s*'
    return re.sub(pattern, '', nombre_raw).strip()


def validar_geometria(gdf):
    if gdf.empty:
        return False, "El archivo está vacío"
    geom = gdf.unary_union
    if not geom.is_valid:
        return False, "La geometría del polígono no es válida"
    bounds = geom.bounds
    if bounds[0] < -85 or bounds[2] > -66 or bounds[1] < -5 or bounds[3] > 15:
        return False, "El polígono parece estar fuera de Colombia"
    return True, "Geometría válida"


def check_dependencias():
    faltantes = []
    if not LXML_OK:
        faltantes.append('lxml')
    if not PYPROJ_OK:
        faltantes.append('pyproj')
    if faltantes:
        return False, f"Faltan librerías: {', '.join(faltantes)}. Agregar al requirements.txt"
    return True, "OK"
