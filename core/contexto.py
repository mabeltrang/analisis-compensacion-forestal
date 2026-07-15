# -*- coding: utf-8 -*-
"""
Módulo de contexto geográfico.
Cruza el polígono de impacto con assets locales y GEE para obtener:
  - Municipio, Departamento  ← local (data/municipios_colombia.fgb.gz)
  - BIOMA-IAvH
  - Zona Hidrográfica (ZH), Subzona (SZH)
  - Áreas por cobertura (IDEAM)
  - Tasa BAU de pérdida de bosque (Hansen) — por municipio, SZH y ZH
"""
import ee
import time
import gzip
import os
import tempfile
import geopandas as gpd
from shapely.geometry import mapping
from shapely.ops import transform, unary_union
from config import settings

HANSEN_DATASET           = 'UMD/hansen/global_forest_change_2025_v1_13'
HANSEN_ANIOS_OBSERVACION = 25
TREECOVER_UMBRAL         = 30

# Ruta al archivo de municipios — se busca en este orden:
#   1. raíz del repo, sin comprimir  (municipios_colombia.fgb)
#   2. raíz del repo, comprimido     (municipios_colombia.fgb.gz)
#   3. carpeta data/, sin comprimir  (data/municipios_colombia.fgb)
#   4. carpeta data/, comprimido     (data/municipios_colombia.fgb.gz)
_DIR_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CANDIDATOS_PATH = [
    (os.path.join(_DIR_REPO, 'municipios_colombia.fgb'),    False),
    (os.path.join(_DIR_REPO, 'municipios_colombia.fgb.gz'), True),
    (os.path.join(_DIR_REPO, 'data', 'municipios_colombia.fgb'),    False),
    (os.path.join(_DIR_REPO, 'data', 'municipios_colombia.fgb.gz'), True),
]

_municipios_gdf = None   # cache en memoria


def _cargar_municipios():
    """Carga el GeoDataFrame de municipios desde disco (con caché)."""
    global _municipios_gdf
    if _municipios_gdf is not None:
        return _municipios_gdf

    ruta, comprimido = None, False
    for path, gz in _CANDIDATOS_PATH:
        if os.path.exists(path):
            ruta, comprimido = path, gz
            break

    if ruta is None:
        raise FileNotFoundError(
            "No se encontró municipios_colombia.fgb(.gz) en la raíz ni en data/. "
            "Descarga el archivo desde el repo y colócalo en la raíz del proyecto."
        )

    if comprimido:
        with gzip.open(ruta, 'rb') as f_in:
            tmp = tempfile.NamedTemporaryFile(suffix='.fgb', delete=False)
            tmp.write(f_in.read())
            tmp.close()
        try:
            _municipios_gdf = gpd.read_file(tmp.name)
        finally:
            os.unlink(tmp.name)
    else:
        _municipios_gdf = gpd.read_file(ruta)

    return _municipios_gdf


def _detectar_municipio_local(gdf_impacto):
    """
    Detecta municipio y departamento haciendo intersección local.
    Devuelve (municipio, departamento) del municipio con mayor área de
    intersección con el polígono de impacto.
    """
    muns = _cargar_municipios()

    # Unión del polígono de impacto
    impacto_union = unary_union(gdf_impacto.geometry)

    # Filtrar solo municipios que toquen el bbox del impacto (rápido)
    bbox = impacto_union.bounds   # (minx, miny, maxx, maxy)
    candidatos = muns.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]].copy()

    if candidatos.empty:
        return 'Desconocido', 'Desconocido'

    # Área de intersección de cada candidato con el polígono de impacto
    candidatos = candidatos.copy()
    candidatos['area_interseccion'] = candidatos.geometry.apply(
        lambda g: g.intersection(impacto_union).area
    )

    mejor = candidatos.sort_values('area_interseccion', ascending=False).iloc[0]
    return mejor['municipio'], mejor['departamento']


def obtener_contexto_impacto(gdf):
    """
    Obtiene contexto geográfico completo del polígono de impacto.
    - Municipio/Depto: detección local (data/municipios_colombia.fgb.gz)
    - ZH/SZH/Bioma/Coberturas/Hansen: GEE
    """
    # ─── Preparar geometría ────────────────────────────────────────
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    else:
        gdf = gdf.to_crs("EPSG:4326")

    def strip_z(geom):
        return transform(lambda x, y, z=None: (x, y), geom)
    gdf['geometry'] = gdf['geometry'].apply(strip_z)

    # ─── Municipio/Depto — detección local ────────────────────────
    municipio, departamento = _detectar_municipio_local(gdf)

    features = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom.is_empty:
            continue
        features.append(ee.Feature(ee.Geometry(mapping(geom))))
    fc      = ee.FeatureCollection(features)
    ee_geom = fc.geometry()

    # ─── Assets GEE ───────────────────────────────────────────────
    municipios  = ee.FeatureCollection(settings.GEE_ASSETS['municipios'])
    zh_col      = ee.FeatureCollection(settings.GEE_ASSETS['zh'])
    ecosistemas = ee.FeatureCollection(settings.GEE_ASSETS['ecosistemas'])

    # ─── ZH/SZH: mayor intersección ───────────────────────────────
    zh_candidatos = zh_col.filterBounds(ee_geom).map(
        lambda f: f.set(
            'area_interseccion',
            f.geometry().intersection(ee_geom, ee.ErrorMargin(1)).area()
        )
    )
    zh_first = zh_candidatos.sort('area_interseccion', False).first()

    # ─── Ecosistemas recortados al área de impacto ─────────────────
    eco_impacto = ecosistemas.filterBounds(ee_geom).map(
        lambda f: f.setGeometry(
            f.geometry().intersection(ee_geom, 1)
        ).set(
            'area_ha',
            f.geometry().intersection(ee_geom, 1).area().divide(10000)
        )
    )

    # ─── LLAMADA 1 — ZH + SZH + Bioma + Coberturas ────────────────
    ctx_dict = ee.Dictionary({
        'nom_zh':     zh_first.get('nom_zh'),
        'nom_szh':    zh_first.get('nom_szh'),
        'biomas':     eco_impacto.reduceColumns(
                          ee.Reducer.frequencyHistogram(), ['BIOMA_IAvH']
                      ).get('histogram'),
        'coberturas': eco_impacto.reduceColumns(
                          ee.Reducer.sum().group(1, 'COBERTURA'),
                          ['area_ha', 'COBERTURA']
                      ).get('groups'),
    })

    time.sleep(1)
    ctx_info = ctx_dict.getInfo()

    nom_zh  = ctx_info.get('nom_zh',  'Desconocido')
    nom_szh = ctx_info.get('nom_szh', 'Desconocido')

    biomas_hist     = ctx_info.get('biomas') or {}
    bioma_principal = (
        max(biomas_hist, key=biomas_hist.get)
        if biomas_hist else 'Desconocido'
    )

    areas_cobertura = {}
    for group in (ctx_info.get('coberturas') or []):
        areas_cobertura[group['COBERTURA']] = group['sum']

    # ─── Geometría del municipio para Hansen — desde GEE ──────────
    # El asset Municipios_Abril_2026_shp usa campo 'MpNombre' (IGAC/DANE)
    # en lugar de 'ADM2_NAME' (FAO/GAUL). Se intenta MpNombre primero;
    # si el asset fuera reemplazado por FAO/GAUL, cambiar a 'ADM2_NAME'.
    time.sleep(1)
    municipio_fc = municipios.filter(ee.Filter.eq('MpNombre', municipio))
    # Fallback: si no hay match con MpNombre, intentar ADM2_NAME
    municipio_geom = ee.Algorithms.If(
        municipio_fc.size().gt(0),
        municipio_fc.first().geometry(),
        municipios.filter(ee.Filter.eq('ADM2_NAME', municipio)).first().geometry()
    )
    municipio_geom = ee.Geometry(municipio_geom)

    # ─── LLAMADA 2 — geometría de la SZH ──────────────────────────
    time.sleep(1)
    szh_geom = zh_col.filter(
        ee.Filter.eq('nom_szh', nom_szh)
    ).first().geometry()

    # ─── LLAMADA 3 — geometría de la ZH ───────────────────────────
    time.sleep(1)
    zh_geom = zh_col.filter(
        ee.Filter.eq('nom_zh', nom_zh)
    ).geometry().dissolve(1)

    # ─── LLAMADA 4 — Hansen BAU por municipio ─────────────────────
    time.sleep(1)
    tasa_bau_mun, fuente_bau_mun = _calcular_tasa_bau(municipio_geom, municipio)

    # ─── LLAMADA 5 — Hansen BAU por SZH ───────────────────────────
    time.sleep(1)
    tasa_bau_szh, fuente_bau_szh = _calcular_tasa_bau(szh_geom, f"SZH {nom_szh}")

    # ─── LLAMADA 6 — Hansen BAU por ZH ────────────────────────────
    time.sleep(1)
    tasa_bau_zh, fuente_bau_zh = _calcular_tasa_bau(zh_geom, f"ZH {nom_zh}")

    return {
        'municipio':            municipio,
        'departamento':         departamento,
        'zh':                   nom_zh,
        'szh':                  nom_szh,
        'bioma_principal':      bioma_principal,
        'areas_cobertura':      areas_cobertura,
        'tasa_bau':             tasa_bau_mun,
        'tasa_bau_fuente':      fuente_bau_mun,
        'tasa_bau_szh':         tasa_bau_szh,
        'tasa_bau_szh_fuente':  fuente_bau_szh,
        'tasa_bau_zh':          tasa_bau_zh,
        'tasa_bau_zh_fuente':   fuente_bau_zh,
        # NUEVO — se exponen para core/iniciativas.py (tab de iniciativas de
        # conservación). Son ee.Geometry ya construidas en este mismo
        # request; exponerlas no dispara ninguna llamada nueva a GEE.
        'municipio_geom':       municipio_geom,
        'szh_geom':             szh_geom,
    }


def _calcular_tasa_bau(geom, nombre):
    """
    Calcula tasa BAU con Hansen GFC sobre cualquier geometría de GEE.
    """
    try:
        hansen      = ee.Image(HANSEN_DATASET)
        treecover   = hansen.select('treecover2000')
        loss        = hansen.select('loss')
        bosque_2000 = treecover.gt(TREECOVER_UMBRAL)
        perdida     = loss.And(bosque_2000)
        area_px_ha  = ee.Image.pixelArea().divide(10000)

        combined = (
            bosque_2000.multiply(area_px_ha).rename('bosque')
            .addBands(perdida.multiply(area_px_ha).rename('perdida'))
        )

        resultado = combined.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geom,
            scale=30,
            maxPixels=1e10,
            bestEffort=True
        ).getInfo()

        bosque_total  = float(resultado.get('bosque')  or 0)
        perdida_total = float(resultado.get('perdida') or 0)

        if bosque_total < 1000:
            return (
                0.005,
                f"{nombre}: bosque insuficiente ({bosque_total:.0f} ha en 2000). "
                f"Usando tasa estimada 0.5%."
            )

        tasa   = perdida_total / (bosque_total * HANSEN_ANIOS_OBSERVACION)
        fuente = (
            f"Hansen GFC 2001-2025 sobre {nombre}: "
            f"{bosque_total:,.0f} ha bosque inicial, "
            f"{perdida_total:,.0f} ha perdidas en {HANSEN_ANIOS_OBSERVACION} años."
        )
        return (tasa, fuente)

    except Exception as e:
        return (
            0.005,
            f"Error calculando Hansen para {nombre} ({str(e)[:80]}). "
            f"Usando 0.5% fallback."
        )
