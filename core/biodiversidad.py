import requests
import pandas as pd
import os
from config import settings

GBIF_API_URL = "https://api.gbif.org/v1/occurrence/search"

TAXONES = {
    'Aves': 'Aves',
    'Plantas': 'Plantae',
    'Mamiferos': 'Mammalia',
    'Reptiles': 'Reptilia',
    'Anfibios': 'Amphibia'
}

def consultar_biodiversidad_zona(gdf_zona):
    """
    Consulta GBIF para una zona especfica (GeoDataFrame).
    """
    if gdf_zona.empty:
        return {}
        
    # Obtener bounding box para la consulta
    bounds = gdf_zona.total_bounds # [minx, miny, maxx, maxy]
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
            
            # 2. Consultas por taxn
            for label, kingdom in TAXONES.items():
                params['kingdomName'] = kingdom
                resp_tax = requests.get(GBIF_API_URL, params=params)
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
