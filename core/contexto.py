# -*- coding: utf-8 -*-
"""
Módulo de contexto geográfico.
Cruza el polígono de impacto con assets de GEE para obtener:
  - Municipio, Departamento
  - BIOMA-IAvH
  - Zona Hidrográfica (ZH), Subzona (SZH)
  - Áreas por cobertura (IDEAM)
  - Tasa BAU de pérdida de bosque (Hansen) — por municipio
"""
import ee
import time
from shapely.geometry import mapping
from shapely.ops import transform
from config import settings

HANSEN_DATASET          = 'UMD/hansen/global_forest_change_2025_v1_13'  # v1.13 actualizado
HANSEN_ANIOS_OBSERVACION = 25   # 2001-2025
TREECOVER_UMBRAL         = 30


def obtener_contexto_impacto(gdf):
    """
    Obtiene contexto geográfico completo del polígono de impacto.
    Usa el mínimo de llamadas .getInfo() posible para evitar Too Many Requests.
    """
    # ─── Preparar geometría ────────────────────────────────────────
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    else:
        gdf = gdf.to_crs("EPSG:4326")

    def strip_z(geom):
        return transform(lambda x, y, z=None: (x, y), geom)
    gdf['geometry'] = gdf['geometry'].apply(strip_z)

    features = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom.is_empty:
            continue
        features.append(ee.Feature(ee.Geometry(mapping(geom))))
    fc      = ee.FeatureCollection(features)
    ee_geom = fc.geometry()

    # ─── Assets ───────────────────────────────────────────────────
    municipios  = ee.FeatureCollection(settings.GEE_ASSETS['municipios'])
    zh_col      = ee.FeatureCollection(settings.GEE_ASSETS['zh'])
    ecosistemas = ee.FeatureCollection(settings.GEE_ASSETS['ecosistemas'])

    mun_first = municipios.filterBounds(ee_geom).first()
    zh_first  = zh_col.filterBounds(ee_geom).first()

    # ─── LLAMADA 1 — todo el contexto geográfico en un solo getInfo ─
    # Municipio + ZH + BIOMA en una sola petición
    eco_impacto = ecosistemas.filterBounds(ee_geom).map(
        lambda f: f.setGeometry(f.geometry().intersection(ee_geom, 1))
                   .set('area_ha', f.geometry().intersection(ee_geom, 1).area().divide(10000))
    )

    ctx_dict = ee.Dictionary({
        'municipio':  mun_first.get('ADM2_NAME'),
        'depto':      mun_first.get('ADM1_NAME'),
        'nom_zh':     zh_first.get('nom_zh'),
        'nom_szh':    zh_first.get('nom_szh'),
        'biomas':     eco_impacto.reduceColumns(
                          ee.Reducer.frequencyHistogram(), ['BIOMA_IAvH']
                      ).get('histogram'),
        'coberturas': eco_impacto.reduceColumns(
                          ee.Reducer.sum().group(1, 'COBERTURA'),
                          ['area_ha', 'COBERTURA']
                      ).get('groups'),
        'mun_geom_id': mun_first.id()   # para recuperar la geometría del municipio
    })

    # Pausa corta antes de la primera petición
    time.sleep(1)
    ctx_info = ctx_dict.getInfo()

    # ─── Parsear resultados de la llamada 1 ────────────────────────
    municipio  = ctx_info.get('municipio', 'Desconocido')
    departamento = ctx_info.get('depto', 'Desconocido')
    nom_zh     = ctx_info.get('nom_zh', 'Desconocido')
    nom_szh    = ctx_info.get('nom_szh', 'Desconocido')

    biomas_hist     = ctx_info.get('biomas') or {}
    bioma_principal = max(biomas_hist, key=biomas_hist.get) if biomas_hist else 'Desconocido'

    areas_cobertura = {}
    for group in (ctx_info.get('coberturas') or []):
        areas_cobertura[group['COBERTURA']] = group['sum']

    # ─── LLAMADA 2 — geometría del municipio para Hansen ──────────
    time.sleep(1)
    municipio_geom = municipios.filter(
        ee.Filter.eq('ADM2_NAME', municipio)
    ).first().geometry()

    # ─── LLAMADA 3 — Hansen BAU (2 reducers consolidados) ─────────
    time.sleep(1)
    tasa_bau, fuente_bau = _calcular_tasa_bau(municipio_geom, municipio)

    return {
        'municipio':       municipio,
        'departamento':    departamento,
        'zh':              nom_zh,
        'szh':             nom_szh,
        'bioma_principal': bioma_principal,
        'areas_cobertura': areas_cobertura,
        'tasa_bau':        tasa_bau,
        'tasa_bau_fuente': fuente_bau,
    }


def _calcular_tasa_bau(geom_municipio, nombre_municipio):
    """
    Calcula tasa BAU con Hansen GFC.
    Consolida los dos reduceRegion en una sola llamada getInfo.
    """
    try:
        hansen      = ee.Image(HANSEN_DATASET)
        treecover   = hansen.select('treecover2000')
        loss        = hansen.select('loss')
        bosque_2000 = treecover.gt(TREECOVER_UMBRAL)
        perdida     = loss.And(bosque_2000)
        area_px_ha  = ee.Image.pixelArea().divide(10000)

        # Consolidar los dos reducers en una sola imagen multibanda → 1 getInfo
        combined = bosque_2000.multiply(area_px_ha).rename('bosque') \
            .addBands(perdida.multiply(area_px_ha).rename('perdida'))

        resultado = combined.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geom_municipio,
            scale=30,
            maxPixels=1e10,
            bestEffort=True
        ).getInfo()

        bosque_total  = float(resultado.get('bosque') or 0)
        perdida_total = float(resultado.get('perdida') or 0)

        if bosque_total < 1000:
            return (
                0.005,
                f"Municipio con poco bosque ({bosque_total:.0f} ha en 2000). "
                f"Usando tasa estimada 0.5%."
            )

        tasa   = perdida_total / (bosque_total * HANSEN_ANIOS_OBSERVACION)
        fuente = (
            f"Hansen GFC 2001-2025 sobre {nombre_municipio}: "
            f"{bosque_total:,.0f} ha bosque inicial, "
            f"{perdida_total:,.0f} ha perdidas en {HANSEN_ANIOS_OBSERVACION} años."
        )
        return (tasa, fuente)

    except Exception as e:
        return (
            0.005,
            f"Error calculando Hansen ({str(e)[:80]}). Usando 0.5% fallback."
        )
