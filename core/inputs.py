import geopandas as gpd
import os
import zipfile
import tempfile
import shutil
from shapely.geometry import shape

def cargar_poligono_impacto(file_obj, filename):
    """
    Carga polgonos desde KMZ, KML o SHP (zip).
    Retorna un GeoDataFrame en WGS84.
    """
    tmp_dir = tempfile.mkdtemp()
    filepath = os.path.join(tmp_dir, filename)
    
    with open(filepath, "wb") as f:
        f.write(file_obj.getbuffer())
        
    try:
        if filename.endswith('.kmz'):
            # Descomprimir KMZ
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                zip_ref.extractall(tmp_dir)
            # Buscar el .kml
            kml_files = [f for f in os.listdir(tmp_dir) if f.endswith('.kml')]
            if kml_files:
                gdf = gpd.read_file(os.path.join(tmp_dir, kml_files[0]), driver='KML')
            else:
                raise ValueError("No se encontr un archivo KML dentro del KMZ")
                
        elif filename.endswith('.kml'):
            gdf = gpd.read_file(filepath, driver='KML')
            
        elif filename.endswith('.zip'):
            # Asumir SHP comprimido
            gdf = gpd.read_file(f"zip://{filepath}")
            
        else:
            raise ValueError("Formato no soportado. Use KMZ, KML o ZIP (SHP)")
            
        # Reproyectar a WGS84
        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)
        else:
            gdf = gdf.to_crs("EPSG:4326")
            
        return gdf
        
    finally:
        shutil.rmtree(tmp_dir)

def validar_geometria(gdf):
    """Valida que el polgono sea vlido y est en Colombia (aprox)"""
    if gdf.empty:
        return False, "El archivo est vaco"
    
    # Unir todos los polgonos en uno solo si hay varios
    geom = gdf.unary_union
    if not geom.is_valid:
        return False, "La geometra del polgono no es vlida"
        
    # Validar lmites de Colombia (aprox)
    bounds = geom.bounds # (minx, miny, maxx, maxy)
    if bounds[0] < -85 or bounds[2] > -66 or bounds[1] < -5 or bounds[3] > 15:
        return False, "El polgono parece estar fuera de Colombia"
        
    return True, "Geometra vlida"
