# -*- coding: utf-8 -*-
import requests
import pandas as pd
import os
from config import settings

GBIF_API_URL = "https://api.gbif.org/v1/occurrence/search"

TAXONES = {
    'Aves':      'Aves',
    'Plantas':   'Magnoliopsida',
    'Mamíferos': 'Mammalia',
    'Reptiles':  'Reptilia',
    'Anfibios':  'Amphibia'
}


def _bounds_from_geojson(geojson):
    """
    Extrae [minx, miny, maxx, maxy] de un GeoJSON de tipo Polygon/MultiPolygon.
    Devuelve None si no es posible.
    """
    if not geojson:
        return None
    try:
        coords_flat = []
        geom_type = geojson.get('type')
        coords = geojson.get('coordinates', [])

        if geom_type == 'Polygon':
            for ring in coords:
                coords_flat.extend(ring)
        elif geom_type == 'MultiPolygon':
            for poly in coords:
                for ring in poly:
                    coords_flat.extend(ring)
        else:
            return None

        xs = [c[0] for c in coords_flat]
        ys = [c[1] for c in coords_flat]
        return [min(xs), min(ys), max(xs), max(ys)]
    except Exception:
        return None


def _wkt_from_bounds(bounds):
    """Convierte bounds [minx, miny, maxx, maxy] a WKT de polígono rectangular."""
    minx, miny, maxx, maxy = bounds
    return (
        f"POLYGON(({minx} {miny}, {maxx} {miny}, "
        f"{maxx} {maxy}, {minx} {maxy}, {minx} {miny}))"
    )


def _consultar_gbif(geometry_wkt, lista_amenazadas):
    """
    Consulta GBIF para un WKT dado.
    Retorna dict con riqueza, taxones y especies amenazadas.
    """
    params = {
        'geometry':         geometry_wkt,
        'country':          'CO',
        'hasCoordinate':    'true',
        'year':             '2010,2024',
        'limit':            1000,
        'occurrenceStatus': 'PRESENT'
    }

    resultado = {
        'riqueza_total':      0,
        'taxones':            {},
        'especies_amenazadas': [],
        'registros_totales':  0
    }

    try:
        response = requests.get(GBIF_API_URL, params=params, timeout=30)
        if response.status_code != 200:
            return resultado

        data = response.json()
        resultado['registros_totales'] = data.get('count', 0)

        especies = {
            occ.get('species')
            for occ in data.get('results', [])
            if occ.get('species')
        }
        resultado['riqueza_total']      = len(especies)
        resultado['especies_amenazadas'] = [sp for sp in especies if sp in lista_amenazadas]

        # Consulta por taxón
        for label, class_name in TAXONES.items():
            params_tax = params.copy()
            if label == 'Plantas':
                params_tax['kingdomName'] = 'Plantae'
            else:
                params_tax['class'] = class_name

            resp_tax = requests.get(GBIF_API_URL, params=params_tax, timeout=30)
            if resp_tax.status_code == 200:
                tax_data  = resp_tax.json()
                tax_spp   = {
                    occ.get('species')
                    for occ in tax_data.get('results', [])
                    if occ.get('species')
                }
                resultado['taxones'][label] = len(tax_spp)
            else:
                resultado['taxones'][label] = 0

    except Exception as e:
        print(f"Error GBIF: {e}")

    return resultado


def consultar_biodiversidad_zona(gdf_zona):
    """
    Consulta GBIF para la zona de IMPACTO (buffer 10 km).
    Retorna dict estándar de biodiversidad.
    """
    gdf_buffer = gdf_zona.to_crs("EPSG:3116").buffer(10000).to_crs("EPSG:4326")
    bounds = gdf_buffer.total_bounds  # [minx, miny, maxx, maxy]
    wkt = _wkt_from_bounds(bounds)

    amenazadas_df  = pd.read_csv(os.path.join(settings.CONFIG_DIR, "especies_amenazadas_co.csv"))
    lista_amenazadas = amenazadas_df['nombre_cientifico'].tolist()

    return _consultar_gbif(wkt, lista_amenazadas)


def consultar_biodiversidad_candidatas(cand_results):
    """
    Consulta GBIF para cada rango candidato usando la geometría
    devuelta por rangos.construir_areas_candidatas (geom_geojson).

    Retorna dict por rango con:
      - bd_conservar: biodiversidad en subzona Natural  (pérdida evitada)
      - bd_restaurar: biodiversidad en subzona Transformada (ganancia potencial)
      - bd_total: biodiversidad en toda la zona del rango
      - adicionalidad_neta: riqueza_candidata - riqueza_impacto (se calcula en app.py)
    """
    amenazadas_df    = pd.read_csv(os.path.join(settings.CONFIG_DIR, "especies_amenazadas_co.csv"))
    lista_amenazadas = amenazadas_df['nombre_cientifico'].tolist()

    resultados = {}

    for rango, datos in cand_results.items():
        geojson = datos.get('geom_geojson')
        bounds  = _bounds_from_geojson(geojson)

        if not bounds:
            resultados[rango] = {
                'bd_total':     {'riqueza_total': 0, 'taxones': {}, 'especies_amenazadas': [], 'registros_totales': 0},
                'error':        'Sin geometría disponible'
            }
            continue

        wkt = _wkt_from_bounds(bounds)

        # Consulta principal para toda la zona del rango
        bd_total = _consultar_gbif(wkt, lista_amenazadas)

        resultados[rango] = {
            'bd_total': bd_total,
        }

    return resultados
