# -*- coding: utf-8 -*-
"""
biodiversidad.py

Consulta GBIF devolviendo LISTAS de especies (no solo conteos),
lo que permite calcular:
  - Métrica B: densidad de amenazadas por hectárea
  - Métrica C: especies únicas en candidata (adicionalidad real)
               y complementariedad respecto a la zona de impacto
"""
import os
import requests
import pandas as pd
from config import settings

GBIF_API_URL = "https://api.gbif.org/v1/occurrence/search"

# ── Taxon keys numéricos correctos de GBIF ───────────────────────────────────
# Usar 'class' (string) no funciona — GBIF lo ignora y devuelve todo.
# Los classKey/kingdomKey son los IDs internos del backbone taxonómico de GBIF.
TAXONES = {
    'Aves':      {'classKey':   212},
    'Plantas':   {'kingdomKey':   6},
    'Mamíferos': {'classKey':   359},
    'Reptiles':  {'classKey':   358},
    'Anfibios':  {'classKey':   131},
}


# ─────────────────────────────────────────────────────────────────────────────
# Geometría: GeoJSON → WKT
# ─────────────────────────────────────────────────────────────────────────────

def _geojson_to_wkt(geojson):
    """
    Convierte un dict GeoJSON Polygon/MultiPolygon (de GEE)
    a WKT válido para el parámetro geometry de GBIF.
    Retorna None si el input es None o no reconocido.
    """
    if not geojson:
        return None
    try:
        geom_type = geojson.get('type')
        coords    = geojson.get('coordinates', [])

        def ring_str(ring):
            return ' '.join(f'{c[0]} {c[1]}' for c in ring)

        if geom_type == 'Polygon':
            rings = ','.join(f'({ring_str(r)})' for r in coords)
            return f'POLYGON({rings})'
        elif geom_type == 'MultiPolygon':
            polys = ','.join(
                '(' + ','.join(f'({ring_str(r)})' for r in poly) + ')'
                for poly in coords
            )
            return f'MULTIPOLYGON({polys})'
        else:
            return None
    except Exception:
        return None


def _bounds_wkt_from_gdf(gdf):
    """WKT del bounding box con buffer 10 km de un GeoDataFrame."""
    buf = gdf.to_crs('EPSG:3116').buffer(10000).to_crs('EPSG:4326')
    minx, miny, maxx, maxy = buf.total_bounds
    return (
        f'POLYGON(({minx} {miny},{maxx} {miny},'
        f'{maxx} {maxy},{minx} {maxy},{minx} {miny}))'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Carga lista de amenazadas
# ─────────────────────────────────────────────────────────────────────────────

def _cargar_amenazadas():
    path = os.path.join(settings.CONFIG_DIR, 'especies_amenazadas_co.csv')
    try:
        df = pd.read_csv(path)
        return set(df['nombre_cientifico'].tolist())
    except Exception:
        return set()


# ─────────────────────────────────────────────────────────────────────────────
# Consulta GBIF núcleo — devuelve SET de especies
# ─────────────────────────────────────────────────────────────────────────────

def _consultar_gbif_especies(wkt):
    """
    Consulta GBIF para un WKT y devuelve el SET de nombres de especies
    registradas (hasta 1000 ocurrencias recientes en Colombia).
    Retorna set vacío si falla o wkt es None.
    """
    if not wkt:
        return set()
    params = {
        'geometry':         wkt,
        'country':          'CO',
        'hasCoordinate':    'true',
        'year':             '2010,2024',
        'limit':            300,
        'occurrenceStatus': 'PRESENT',
    }
    try:
        resp = requests.get(GBIF_API_URL, params=params, timeout=30)
        if resp.status_code != 200:
            return set()
        resultados = resp.json().get('results', [])
        return {r.get('species') for r in resultados if r.get('species')}
    except Exception as e:
        print(f'[GBIF] Error: {e}')
        return set()


def _consultar_por_taxon(wkt):
    """
    Consulta GBIF separada por grupo taxonómico usando classKey/kingdomKey.
    Retorna dict {grupo: set_de_especies}.
    """
    if not wkt:
        return {k: set() for k in TAXONES}

    params_base = {
        'geometry':         wkt,
        'country':          'CO',
        'hasCoordinate':    'true',
        'year':             '2010,2024',
        'limit':            300,
        'occurrenceStatus': 'PRESENT',
    }
    resultado = {}
    for label, filtro in TAXONES.items():
        p = {**params_base, **filtro}
        try:
            r = requests.get(GBIF_API_URL, params=p, timeout=30)
            if r.status_code == 200:
                spp = {
                    o.get('species')
                    for o in r.json().get('results', [])
                    if o.get('species')
                }
                resultado[label] = spp
            else:
                resultado[label] = set()
        except Exception:
            resultado[label] = set()
    return resultado


# ─────────────────────────────────────────────────────────────────────────────
# Métricas B y C
# ─────────────────────────────────────────────────────────────────────────────

def calcular_metricas(
    especies_zona,
    especies_impacto,
    area_zona_ha,
    area_impacto_ha,
    amenazadas_set,
):
    """
    Calcula métricas de adicionalidad biótica para una zona candidata.

    Métrica B — Densidad de amenazadas por hectárea:
        densidad_amenazadas_zona    vs.  densidad_amenazadas_impacto
        Si zona > impacto → adicionalidad positiva en amenazadas.

    Métrica C — Complementariedad (especies únicas):
        unicas_zona = especies en zona que NO están en impacto
        complementariedad = |unicas_zona| / |zona ∪ impacto|
        → Qué fracción de la biodiversidad de compensación es genuinamente nueva.

    Retorna dict con todos los valores calculados.
    """
    amenazadas_zona    = especies_zona    & amenazadas_set
    amenazadas_impacto = especies_impacto & amenazadas_set

    # ── Métrica B ──
    dens_zona    = len(amenazadas_zona)    / max(area_zona_ha,    1)
    dens_impacto = len(amenazadas_impacto) / max(area_impacto_ha, 1)
    ratio_b      = dens_zona / max(dens_impacto, 1e-9)

    # ── Métrica C ──
    unicas_zona = especies_zona - especies_impacto
    union       = especies_zona | especies_impacto
    complement  = len(unicas_zona) / max(len(union), 1)  # 0..1

    # ── Score combinado (B+C) para semáforo ──
    # Promedio ponderado: 60% complementariedad, 40% ratio amenazadas (cap 2×)
    score = 0.6 * complement + 0.4 * min(ratio_b, 2) / 2

    return {
        # Conteos
        'riqueza_zona':         len(especies_zona),
        'riqueza_impacto':      len(especies_impacto),
        'amenazadas_zona':      sorted(amenazadas_zona),
        'amenazadas_impacto':   sorted(amenazadas_impacto),
        'n_amenazadas_zona':    len(amenazadas_zona),
        'n_amenazadas_impacto': len(amenazadas_impacto),
        # Especies únicas (adicionalidad C)
        'unicas_zona':          sorted(unicas_zona),
        'n_unicas':             len(unicas_zona),
        'complementariedad':    round(complement, 3),
        # Densidad amenazadas (adicionalidad B)
        'dens_amenazadas_zona': round(dens_zona,    5),
        'dens_amenazadas_imp':  round(dens_impacto, 5),
        'ratio_amenazadas':     round(ratio_b, 3),
        # Score final
        'score_bc':  round(score, 3),
        'valoracion': (
            '🟢 Alta'  if score > 0.5 else
            '🟡 Media' if score > 0.2 else
            '🔴 Baja'
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────

def consultar_biodiversidad_zona(gdf_zona):
    """
    GBIF para la zona de IMPACTO (buffer 10 km).
    Retorna dict con especies (set), conteos por taxón y amenazadas.
    """
    amenazadas = _cargar_amenazadas()
    wkt        = _bounds_wkt_from_gdf(gdf_zona)
    por_taxon  = _consultar_por_taxon(wkt)

    # Unión de todas las especies de todos los grupos
    especies = set()
    for spp_set in por_taxon.values():
        especies |= spp_set

    return {
        'wkt':                 wkt,
        'especies':            especies,
        'riqueza_total':       len(especies),
        'taxones':             {k: len(v) for k, v in por_taxon.items()},
        'especies_amenazadas': sorted(especies & amenazadas),
        'registros_totales':   len(especies),
    }


def consultar_biodiversidad_candidatas(cand_results, bd_impacto, progress_callback=None):
    """
    GBIF para cada rango candidato, separando Conservar y Restaurar.
    Calcula métricas B+C comparando con la zona de impacto.

    cand_results : dict de rangos.construir_areas_candidatas()
    bd_impacto   : dict de consultar_biodiversidad_zona()
    progress_callback(rango, i, total) : opcional

    Retorna dict {rango: {conservar: {...}, restaurar: {...}, total: {...}}}
    """
    amenazadas   = _cargar_amenazadas()
    especies_imp = bd_impacto.get('especies', set())

    # Área de impacto: suma de riqueza como proxy de ha (se usa solo para densidad)
    area_impacto_ha = max(bd_impacto.get('riqueza_total', 1), 1)

    resultados = {}
    total      = len(cand_results)

    for i, (rango, datos) in enumerate(cand_results.items()):
        if progress_callback:
            progress_callback(rango, i, total)

        ha_cons = max(datos.get('ha_conservar', 1), 1)
        ha_rest = max(datos.get('ha_restaurar', 1), 1)
        ha_tot  = max(datos.get('total',        1), 1)

        wkt_cons = _geojson_to_wkt(datos.get('geom_conservar'))
        wkt_rest = _geojson_to_wkt(datos.get('geom_restaurar'))
        wkt_tot  = _geojson_to_wkt(datos.get('geom_total'))

        spp_cons = _consultar_gbif_especies(wkt_cons)
        spp_rest = _consultar_gbif_especies(wkt_rest)
        spp_tot  = _consultar_gbif_especies(wkt_tot)

        resultados[rango] = {
            'conservar': calcular_metricas(
                spp_cons, especies_imp, ha_cons, area_impacto_ha, amenazadas
            ),
            'restaurar': calcular_metricas(
                spp_rest, especies_imp, ha_rest, area_impacto_ha, amenazadas
            ),
            'total': calcular_metricas(
                spp_tot, especies_imp, ha_tot, area_impacto_ha, amenazadas
            ),
        }

    if progress_callback:
        progress_callback('Listo', total, total)

    return resultados
