import requests
import pandas as pd
import os
from config import settings

GBIF_API_URL = "https://api.gbif.org/v1/occurrence/search"

TAXONES = {
    'Aves': 'Aves',
    'Plantas': 'Magnoliopsida', # Clase representativa para plantas vasculares
    'Mamíferos': 'Mammalia',
    'Reptiles': 'Reptilia',
    'Anfibios': 'Amphibia'
}

def consultar_biodiversidad_zona(gdf_zona):
    """
    Consulta GBIF para una zona especfica (GeoDataFrame).
    """
    # 1. Crear un buffer de 10km alrededor de la zona para tener una caracterización regional
    # Necesitamos proyectar temporalmente a metros (EPSG:3116 o similar) para el buffer
    gdf_buffer = gdf_zona.to_crs("EPSG:3116").buffer(10000).to_crs("EPSG:4326")
    bounds = gdf_buffer.total_bounds # [minx, miny, maxx, maxy]
    
    # Formato WKT para GBIF
    geometry_wkt = f"POLYGON(({bounds[0]} {bounds[1]}, {bounds[2]} {bounds[1]}, {bounds[2]} {bounds[3]}, {bounds[0]} {bounds[3]}, {bounds[0]} {bounds[1]}))"
    
    resultados = {
        'riqueza_total': 0,
        'taxones': {},
        'especies_amenazadas': [],
        'registros_totales': 0
    }
    
    # Cargar especies amenazadas para cruce
    amenazadas_df = pd.read_csv(os.path.join(settings.CONFIG_DIR, "especies_amenazadas_co.csv"))
    lista_amenazadas = amenazadas_df['nombre_cientifico'].tolist()
    
    try:
        # 1. Consulta general para riqueza y registros
        params = {
            'geometry': geometry_wkt,
            'country': 'CO',
            'hasCoordinate': 'true',
            'year': '2010,2024',
            'limit': 1000,
            'occurrenceStatus': 'PRESENT'
        }
        
        response = requests.get(GBIF_API_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            resultados['registros_totales'] = data.get('count', 0)
            
            # Obtener especies nicas
            especies = {occ.get('species') for occ in data.get('results', []) if occ.get('species')}
            resultados['riqueza_total'] = len(especies)
            
            # Identificar amenazadas en la zona
            resultados['especies_amenazadas'] = [sp for sp in especies if sp in lista_amenazadas]
            
            # 2. Consultas por taxón (Clases)
            for label, class_name in TAXONES.items():
                params_tax = params.copy()
                if label == 'Plantas':
                    params_tax['kingdomName'] = 'Plantae'
                else:
                    params_tax['classKey'] = class_name # Error corregido: GBIF usa classKey para Aves, etc.
                    # Nota: GBIF API a veces requiere el ID numrico, pero intentamos con nombre
                    # Si falla, usamos el parmetro 'class'
                    params_tax.pop('classKey', None)
                    params_tax['class'] = class_name
                
                resp_tax = requests.get(GBIF_API_URL, params=params_tax)
                if resp_tax.status_code == 200:
                    tax_data = resp_tax.json()
                    tax_especies = {occ.get('species') for occ in tax_data.get('results', []) if occ.get('species')}
                    resultados['taxones'][label] = len(tax_especies)
                else:
                    resultados['taxones'][label] = 0
                    
        return resultados
        
    except Exception as e:
        print(f"Error en consulta GBIF: {e}")
        return resultados
